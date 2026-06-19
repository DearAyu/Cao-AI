from rest_framework import status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ImageJob, VideoJob
from .prompt_analysis import PromptAnalysisError, analyze_product_image
from .prompt_serializers import PromptAnalysisRequestSerializer
from .serializers import ImageJobSerializer, VideoJobSerializer
from .services import refresh_image_job, refresh_job, submit_image_job, submit_job


class PromptAnalysisView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = PromptAnalysisRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            prompt = analyze_product_image(serializer.validated_data["image"])
        except PromptAnalysisError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY
            )
        return Response({"prompt": prompt})


class VideoJobViewSet(viewsets.ModelViewSet):
    queryset = VideoJob.objects.all()
    serializer_class = VideoJobSerializer
    http_method_names = ["get", "post", "head", "options"]

    def list(self, request, *args, **kwargs):
        jobs = self.get_queryset()[:20]
        serializer = self.get_serializer(jobs, many=True)
        return Response({"results": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = serializer.save()
        submit_job(job)
        return Response(self.get_serializer(job).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        job = self.get_object()
        refresh_job(job)
        return Response(self.get_serializer(job).data)


class ImageJobViewSet(viewsets.ModelViewSet):
    queryset = ImageJob.objects.all()
    serializer_class = ImageJobSerializer
    http_method_names = ["get", "post", "head", "options"]

    def list(self, request, *args, **kwargs):
        jobs = self.get_queryset()[:20]
        serializer = self.get_serializer(jobs, many=True)
        return Response({"results": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = serializer.save()
        submit_image_job(job)
        return Response(self.get_serializer(job).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        job = self.get_object()
        refresh_image_job(job)
        return Response(self.get_serializer(job).data)
