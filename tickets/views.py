from rest_framework import viewsets, status, permissions
from django.shortcuts import render
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Count, Q, Avg, Case, When, Min, Max
from datetime import timedelta
from django.contrib.auth import get_user_model
from .models import Ticket, Comment
from .serializers import (
    TicketSerializer, CommentSerializer, 
    TicketAssignmentSerializer, TicketStatusSerializer
)
from .permissions import (
    IsTicketOwnerOrAssigned, IsAdmin, CanAssignTicket
)

User = get_user_model()

def welcome_view(request):
    """Serve the welcome page for the root URL"""
    return render(request, 'welcome.html')

class TicketViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tickets.
    """
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'priority', 'assigned_to']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'priority']
    
    
    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Ticket.objects.none()
            
        if user.role == 'admin':
            return Ticket.objects.all()
        elif user.role == 'agent':
            return Ticket.objects.filter(
                Q(assigned_to=user) | Q(created_by=user)
            ).distinct()
        else:
            return Ticket.objects.filter(created_by=user)
    
    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [IsTicketOwnerOrAssigned]
        elif self.action == 'destroy':
            permission_classes = [IsAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated, IsTicketOwnerOrAssigned]
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        ticket = serializer.save(created_by=self.request.user)
        # Schedule escalation check
        from .tasks import check_ticket_escalation
        check_ticket_escalation.apply_async(
            (ticket.id,), 
            countdown=ticket.get_escalation_timeframe() * 3600
        )
    
    @action(detail=True, methods=['post'], permission_classes=[CanAssignTicket])
    def assign(self, request, pk=None):
        ticket = self.get_object()
        serializer = TicketAssignmentSerializer(ticket, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsTicketOwnerOrAssigned])
    def add_comment(self, request, pk=None):
        ticket = self.get_object()
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, ticket=ticket)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing comments on tickets.
    """
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated, IsTicketOwnerOrAssigned]
    
    def get_queryset(self):
        return Comment.objects.filter(ticket__id=self.kwargs['ticket_pk'])
    
    def perform_create(self, serializer):
        ticket = Ticket.objects.get(id=self.kwargs['ticket_pk'])
        serializer.save(user=self.request.user, ticket=ticket)

class ReportViewSet(viewsets.ViewSet):
    """
    ViewSet for generating various reports and analytics.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def get_queryset(self):
        """Base queryset filtered by user permissions"""
        user = self.request.user
        if user.role == 'admin':
            return Ticket.objects.all()
        elif user.role == 'agent':
            return Ticket.objects.filter(assigned_to=user)
        else:
            return Ticket.objects.filter(created_by=user)
    
    @action(detail=False, methods=['get'])
    def weekly_stats(self, request):
        """
        Get ticket statistics for the last 7 days.
        Example: GET /api/reports/weekly_stats/
        """
        seven_days_ago = timezone.now() - timedelta(days=7)
        queryset = self.get_queryset().filter(created_at__gte=seven_days_ago)
        
        stats = queryset.aggregate(
            total_tickets=Count('id'),
            open_tickets=Count('id', filter=Q(status='open')),
            in_progress_tickets=Count('id', filter=Q(status='in_progress')),
            resolved_tickets=Count('id', filter=Q(status='resolved')),
            escalated_tickets=Count('id', filter=Q(status='escalated')),
            closed_tickets=Count('id', filter=Q(status='closed')),
            high_priority=Count('id', filter=Q(priority='high')),
            medium_priority=Count('id', filter=Q(priority='medium')),
            low_priority=Count('id', filter=Q(priority='low')),
        )
        
        # Calculate resolution rate
        total_resolved = stats['resolved_tickets'] + stats['closed_tickets']
        stats['resolution_rate'] = round(
            (total_resolved / stats['total_tickets'] * 100) if stats['total_tickets'] > 0 else 0, 
            2
        )
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def daily_trends(self, request):
        """
        Get daily ticket trends for the last 30 days.
        Example: GET /api/reports/daily_trends/
        """
        thirty_days_ago = timezone.now() - timedelta(days=30)
        queryset = self.get_queryset().filter(created_at__gte=thirty_days_ago)
        
        daily_stats = queryset.annotate(
            day=TruncDay('created_at')
        ).values('day').annotate(
            tickets_created=Count('id'),
            tickets_resolved=Count('id', filter=Q(status__in=['resolved', 'closed'])),
            tickets_escalated=Count('id', filter=Q(status='escalated'))
        ).order_by('day')
        
        return Response(daily_stats)
    
    @action(detail=False, methods=['get'])
    def agent_performance(self, request):
        """
        Get agent performance metrics for the last 30 days.
        Example: GET /api/reports/agent_performance/
        """
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Get agents with their performance metrics
        agents = User.objects.filter(role='agent').annotate(
            total_assigned=Count('assigned_tickets', 
                               filter=Q(assigned_tickets__created_at__gte=thirty_days_ago)),
            total_resolved=Count('assigned_tickets', 
                               filter=Q(assigned_tickets__status__in=['resolved', 'closed']) &
                               Q(assigned_tickets__created_at__gte=thirty_days_ago)),
            total_escalated=Count('assigned_tickets', 
                                filter=Q(assigned_tickets__status='escalated') &
                                Q(assigned_tickets__created_at__gte=thirty_days_ago))
        )
        
        # Calculate average resolution time
        agent_data = []
        for agent in agents:
            # Calculate average resolution time for this agent
            resolved_tickets = Ticket.objects.filter(
                assigned_to=agent,
                status__in=['resolved', 'closed'],
                created_at__gte=thirty_days_ago,
                resolved_at__isnull=False
            )
            
            total_seconds = 0
            count = 0
            for ticket in resolved_tickets:
                if ticket.resolved_at and ticket.created_at:
                    duration = ticket.resolved_at - ticket.created_at
                    total_seconds += duration.total_seconds()
                    count += 1
            
            avg_resolution_hours = (total_seconds / count / 3600) if count > 0 else 0
            
            resolution_rate = round(
                (agent.total_resolved / agent.total_assigned * 100) if agent.total_assigned > 0 else 0, 
                2
            )
            
            agent_data.append({
                'agent_id': agent.id,
                'agent_name': f"{agent.first_name} {agent.last_name}",
                'email': agent.email,
                'total_assigned': agent.total_assigned,
                'total_resolved': agent.total_resolved,
                'total_escalated': agent.total_escalated,
                'resolution_rate': resolution_rate,
                'avg_resolution_hours': round(avg_resolution_hours, 2)
            })
        
        return Response(agent_data)
    
    @action(detail=False, methods=['get'])
    def priority_analysis(self, request):
        """
        Analyze ticket distribution and performance by priority.
        Example: GET /api/reports/priority_analysis/
        """
        thirty_days_ago = timezone.now() - timedelta(days=30)
        queryset = self.get_queryset().filter(created_at__gte=thirty_days_ago)
        
        priority_stats = []
        for priority in ['high', 'medium', 'low']:
            priority_tickets = queryset.filter(priority=priority)
            
            stats = priority_tickets.aggregate(
                total_tickets=Count('id'),
                resolved_tickets=Count('id', filter=Q(status__in=['resolved', 'closed'])),
                escalated_tickets=Count('id', filter=Q(status='escalated'))
            )
            
            # Calculate average resolution time for this priority
            resolved_tickets = priority_tickets.filter(
                status__in=['resolved', 'closed'],
                resolved_at__isnull=False
            )
            
            total_seconds = 0
            count = 0
            for ticket in resolved_tickets:
                if ticket.resolved_at and ticket.created_at:
                    duration = ticket.resolved_at - ticket.created_at
                    total_seconds += duration.total_seconds()
                    count += 1
            
            avg_resolution_hours = (total_seconds / count / 3600) if count > 0 else 0
            resolution_rate = round(
                (stats['resolved_tickets'] / stats['total_tickets'] * 100) if stats['total_tickets'] > 0 else 0, 
                2
            )
            
            priority_stats.append({
                'priority': priority,
                'total_tickets': stats['total_tickets'],
                'resolved_tickets': stats['resolved_tickets'],
                'escalated_tickets': stats['escalated_tickets'],
                'resolution_rate': resolution_rate,
                'avg_resolution_hours': round(avg_resolution_hours, 2)
            })
        
        return Response(priority_stats)
    
    @action(detail=False, methods=['get'])
    def status_distribution(self, request):
        """
        Get current distribution of tickets by status.
        Example: GET /api/reports/status_distribution/
        """
        queryset = self.get_queryset()
        total_count = queryset.count()
        
        status_distribution = queryset.values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Format the data
        formatted_data = []
        for item in status_distribution:
            percentage = round((item['count'] / total_count * 100), 2) if total_count > 0 else 0
            formatted_data.append({
                'status': item['status'],
                'count': item['count'],
                'percentage': percentage
            })
        
        return Response(formatted_data)
    
    @action(detail=False, methods=['get'])
    def response_time_metrics(self, request):
        """
        Get average response time metrics for tickets.
        Example: GET /api/reports/response_time_metrics/
        """
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Get tickets with comments in the last 30 days
        tickets_with_comments = Ticket.objects.filter(
            created_at__gte=thirty_days_ago,
            comments__isnull=False
        ).distinct()
        
        metrics = {
            'avg_first_response_hours': 0,
            'min_first_response_hours': 0,
            'max_first_response_hours': 0
        }
        
        response_times = []
        for ticket in tickets_with_comments:
            first_comment = ticket.comments.order_by('created_at').first()
            if first_comment and ticket.created_at:
                response_time = first_comment.created_at - ticket.created_at
                response_times.append(response_time.total_seconds())
        
        if response_times:
            metrics['avg_first_response_hours'] = round(sum(response_times) / len(response_times) / 3600, 2)
            metrics['min_first_response_hours'] = round(min(response_times) / 3600, 2)
            metrics['max_first_response_hours'] = round(max(response_times) / 3600, 2)
        
        return Response(metrics)
    
    @action(detail=False, methods=['get'])
    def custom_time_range(self, request):
        """
        Get ticket statistics for a custom time range.
        Example: GET /api/reports/custom_time_range/?start_date=2024-01-01&end_date=2024-01-31
        """
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if not start_date or not end_date:
            return Response(
                {"error": "Both start_date and end_date parameters are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            start = timezone.datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            end = timezone.datetime.strptime(end_date, '%Y-%m-%d').replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(created_at__range=[start, end])
        
        stats = queryset.aggregate(
            total_tickets=Count('id'),
            opened_tickets=Count('id'),
            resolved_tickets=Count('id', filter=Q(status__in=['resolved', 'closed'])),
            escalated_tickets=Count('id', filter=Q(status='escalated')),
            high_priority=Count('id', filter=Q(priority='high')),
            medium_priority=Count('id', filter=Q(priority='medium')),
            low_priority=Count('id', filter=Q(priority='low')),
        )
        
        # Add date range info
        stats['date_range'] = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        return Response(stats)