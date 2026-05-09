from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .exceptions import EmailAlreadyExistsError, LicenseLimitExceededError, UserNotFoundError
from .models import CustomUser
from .permissions import IsAdminTenant
from .serializers import (
    ChangePasswordSerializer,
    CreateUserSerializer,
    ProfileSerializer,
    ProfileUpdateSerializer,
    UpdateUserSerializer,
    UserSerializer,
)
from .services import UserManagementService
from .tokens import CustomTokenObtainPairSerializer


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RefreshView(TokenRefreshView):
    pass


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'detail': 'Refresh token requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            return Response({'detail': 'Token inválido o expirado.'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserManagementViewSet(ViewSet):
    permission_classes = [IsAdminTenant]
    service = UserManagementService()

    def list(self, request):
        users = CustomUser.objects.all()
        return Response(UserSerializer(users, many=True).data)

    def retrieve(self, request, pk=None):
        try:
            user = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'No encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(UserSerializer(user).data)

    def create(self, request):
        serializer = CreateUserSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            user = self.service.create_user(
                nombre_completo=d['nombre_completo'],
                email=d['email'],
                password=d['password'],
                role=d['role'],
                tenant=request.tenant,
            )
        except LicenseLimitExceededError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except EmailAlreadyExistsError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        serializer = UpdateUserSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            user = self.service.update_user(
                user_id=pk,
                nombre_completo=d.get('nombre_completo'),
                email=d.get('email'),
                role=d.get('role'),
            )
        except UserNotFoundError:
            return Response({'detail': 'No encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        except EmailAlreadyExistsError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UserSerializer(user).data)

    def deactivate(self, request, pk=None):
        try:
            user = self.service.deactivate_user(user_id=pk)
        except UserNotFoundError:
            return Response({'detail': 'No encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(UserSerializer(user).data)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(ProfileSerializer(request.user).data)

    def put(self, request):
        serializer = ProfileUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        user = request.user
        if 'email' in d:
            if CustomUser.objects.exclude(pk=user.pk).filter(email=d['email']).exists():
                return Response({'email': ['Este email ya está en uso.']}, status=status.HTTP_400_BAD_REQUEST)
            user.email = d['email']
        if 'nombre_completo' in d:
            user.nombre_completo = d['nombre_completo']
        user.save()
        return Response(ProfileSerializer(user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        if not user.check_password(serializer.validated_data['current_password']):
            return Response(
                {'current_password': ['La contraseña actual es incorrecta.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response(status=status.HTTP_200_OK)
