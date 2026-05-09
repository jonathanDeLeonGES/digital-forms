from django.urls import path

from .views import (
    ChangePasswordView,
    LoginView,
    LogoutView,
    ProfileView,
    RefreshView,
    UserManagementViewSet,
)

users_list = UserManagementViewSet.as_view({'get': 'list', 'post': 'create'})
users_detail = UserManagementViewSet.as_view({'get': 'retrieve', 'put': 'update'})
users_deactivate = UserManagementViewSet.as_view({'post': 'deactivate'})

urlpatterns = [
    path('api/auth/login/', LoginView.as_view(), name='auth-login'),
    path('api/auth/refresh/', RefreshView.as_view(), name='auth-refresh'),
    path('api/auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('api/users/', users_list, name='users-list'),
    path('api/users/me/', ProfileView.as_view(), name='users-me'),
    path('api/users/me/change-password/', ChangePasswordView.as_view(), name='users-change-password'),
    path('api/users/<int:pk>/', users_detail, name='users-detail'),
    path('api/users/<int:pk>/deactivate/', users_deactivate, name='users-deactivate'),
]
