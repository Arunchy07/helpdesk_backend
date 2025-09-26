# helpdesksystem/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from rest_framework_nested import routers as nested_routers
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from users.views import UserViewSet
from tickets.views import TicketViewSet, CommentViewSet, ReportViewSet, welcome_view

# Create main router
router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'tickets', TicketViewSet)
router.register(r'reports', ReportViewSet, basename='report')

# Create nested router for comments
ticket_router = nested_routers.NestedDefaultRouter(router, r'tickets', lookup='ticket')
ticket_router.register(r'comments', CommentViewSet, basename='ticket-comments')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', welcome_view, name='welcome'),
    path('api/auth/', include('rest_framework.urls')),
    path('api/', include(router.urls)),
    path('api/', include(ticket_router.urls)),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]