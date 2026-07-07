from typing import Dict, Type

from croploraApp.serializers.auth_serializers import (
    RegisterSerializer, ResendVerificationCodeSerializer,
    UserProfileSerializer, VerifyEmailSerializer, LoginSerializer)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .utils.verification import generate_and_send_verification_code,onboarding_pending,verification_pending


class AuthViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer]
    http_method_names = ["post"]
    serializer_class = LoginSerializer

    action_serializer_map: Dict[str, Type] = {
        "sign_up": RegisterSerializer,
        "verify_email": VerifyEmailSerializer,
        "resend_verification": ResendVerificationCodeSerializer,
        "sign-in":LoginSerializer
    }

    def get_permissions(self):
        if self.action in ["verify_email", "resend_verification"]:
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_serializer_class(self):
        return self.action_serializer_map.get(self.action, self.serializer_class)

    def get_serializer_context(self):
        return {"request": self.request}

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = self.get_serializer_context()
        return self.get_serializer_class()(*args, **kwargs)

    @action(detail=False, methods=["POST"], url_path="sign-up")
    def sign_up(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        generate_and_send_verification_code(user)

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        return Response(
            {
                "message": "Registration successful.",
                "token": str(access),
                "refresh": str(refresh),
                "verification_pending": verification_pending(user),
                "onboarding_pending": onboarding_pending(user),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["POST"], url_path="sign-in")
    def sign_in(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        profile_serializer = UserProfileSerializer(user)

        return Response(
            {
                "token": str(access),
                "refresh": str(refresh),
                "user": profile_serializer.data,
                "verification_pending": verification_pending(user),
                "onboarding_pending": onboarding_pending(user),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["POST"], url_path="verify-email")
    def verify_email(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "message": "Email verified successfully.",
                "onboarding_pending": onboarding_pending(request.user),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["POST"], url_path="resend-verification")
    def resend_verification(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Verification code sent."},
            status=status.HTTP_200_OK,
        )
