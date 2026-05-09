from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import IshikawaView, IssueViewSet

router = DefaultRouter()
router.register(r'api/issues', IssueViewSet, basename='issue')

urlpatterns = router.urls + [
    path('api/issues/<int:pk>/ishikawa/', IshikawaView.as_view(), name='issue-ishikawa'),
]
