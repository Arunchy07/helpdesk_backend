from rest_framework import serializers
from .models import Ticket, Comment

class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = Comment
        fields = ('id', 'user', 'user_name', 'content', 'created_at', 'updated_at')
        read_only_fields = ('user', 'created_at', 'updated_at')

class TicketSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Ticket
        fields = ('id', 'title', 'description', 'priority', 'status', 'created_by', 
                 'created_by_name', 'assigned_to', 'assigned_to_name', 'created_at', 
                 'updated_at', 'resolved_at', 'escalation_date', 'comments')
        read_only_fields = ('created_by', 'created_at', 'updated_at', 'resolved_at', 'escalation_date')

class TicketAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ('assigned_to',)

class TicketStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ('status',)
        
class AgentPerformanceSerializer(serializers.Serializer):
    agent_id = serializers.IntegerField()
    agent_name = serializers.CharField()
    email = serializers.EmailField()
    total_assigned = serializers.IntegerField()
    total_resolved = serializers.IntegerField()
    total_escalated = serializers.IntegerField()
    resolution_rate = serializers.FloatField()
    avg_resolution_hours = serializers.FloatField()

class PriorityAnalysisSerializer(serializers.Serializer):
    priority = serializers.CharField()
    total_tickets = serializers.IntegerField()
    resolved_tickets = serializers.IntegerField()
    escalated_tickets = serializers.IntegerField()
    resolution_rate = serializers.FloatField()
    avg_resolution_hours = serializers.FloatField()

class StatusDistributionSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()