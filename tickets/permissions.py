from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.created_by == request.user

class IsAgent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['agent', 'admin']

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'

class IsTicketOwnerOrAssigned(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        if request.user.role == 'agent':
            return obj.assigned_to == request.user or obj.created_by == request.user
        return obj.created_by == request.user

class CanAssignTicket(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ['agent', 'admin']