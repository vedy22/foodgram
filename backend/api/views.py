from io import BytesIO

from django.contrib.auth import get_user_model
from django.db.models.aggregates import Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from recipes.models import (FavouriteRecipe, Ingredient, Recipe,
                            RecipeIngredient, ShoppingCart, Tag)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from users.models import Follow

from .filters import IngredientFilter, RecipeFilter
from .pagination import CustomPageNumberPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (CreateSubscribeSerializer, IngredientSerializer,
                          RecipeReadSerializer, RecipeWriteSerializer,
                          ShortRecipeSerializer, SubscriptionSerializer,
                          TagsSerializer)

User = get_user_model()


class TagsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagsSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = CustomPageNumberPagination

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=(IsAuthorOrReadOnly,)
    )
    def favorite(self, request, pk):
        if request.method == "POST":
            return self.add_to(FavouriteRecipe, request.user, pk)
        return self.delete_from(FavouriteRecipe, request.user, pk)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=(IsAuthorOrReadOnly,)
    )
    def shopping_cart(self, request, pk):
        if request.method == "POST":
            return self.add_to(ShoppingCart, request.user, pk)
        return self.delete_from(ShoppingCart, request.user, pk)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=(IsAuthenticated,),
        url_path="download_shopping_cart",
        url_name="download_shopping_cart",
    )
    def download_shopping_cart(self, request):
        pdfmetrics.registerFont(TTFont("DejaVuSans", "DejaVuSans.ttf"))
        pdfmetrics.registerFont(
            TTFont("DejaVuSans-Bold", "DejaVuSans-Bold.ttf")
        )

        recipes = (
            RecipeIngredient.objects.filter(
                recipe__shopping_cart__user=request.user
            )
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(sum_total=Sum("amount"))
        )
        if recipes:
            buffer = BytesIO()
            pdf = canvas.Canvas(buffer)
            pdf.setFont("DejaVuSans-Bold", 16)
            pdf.drawString(200, 800, "Список покупок:")
            y_position = 750
            pdf.setFont("DejaVuSans", 12)
            for index, ingredient in enumerate(recipes, start=1):
                text = (
                    f"{index}. "
                    f'{ingredient["ingredient__name"]} '
                    f'{ingredient["sum_total"]} '
                    f'{ingredient["ingredient__measurement_unit"]}.'
                )
                pdf.drawString(200, y_position, text)
                y_position -= 20
            pdf.save()
            buffer.seek(0)
        buffer = BytesIO()
        response = FileResponse(
            buffer, as_attachment=True, filename="shopping_cart.pdf"
        )
        return response

    @staticmethod
    def add_to(model, user, pk):
        if model.objects.filter(user=user, recipe__id=pk).exists():
            return Response(
                {"errors": "Рецепт уже добавлен."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not Recipe.objects.filter(id=pk).exists():
            return Response(
                {"errors": "Такого рецепта не существует."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recipe = get_object_or_404(Recipe, id=pk)
        model.objects.create(user=user, recipe=recipe)
        serializer = ShortRecipeSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def delete_from(model, user, pk) -> Response:
        recipe = get_object_or_404(Recipe, pk=pk)
        obj = model.objects.filter(user=user, recipe=recipe)
        if obj.exists():
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {"errors": "Нет такого рецепта."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class IngredientsVewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()
    pagination_class = CustomPageNumberPagination

    @action(
        detail=False,
        methods=("get",),
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=SubscriptionSerializer,
    )
    def subscriptions(self, request):
        user = self.request.user
        user_subscriptions = user.follower.all()
        authors = user_subscriptions.values_list('author_id', flat=True)
        queryset = User.objects.filter(pk__in=authors)
        paginated_queryset = self.paginate_queryset(queryset)
        serializer = self.get_serializer(paginated_queryset, many=True)
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=("post", "delete"),
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=SubscriptionSerializer,
    )
    def subscribe(self, request, id=None):
        user = self.request.user
        author = get_object_or_404(User, pk=id)
        if self.request.method == "POST":
            serializer = CreateSubscribeSerializer(
                data={'author': author.id, 'user': user.id},
                context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            serializer = SubscriptionSerializer(
                author, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        subscription = Follow.objects.filter(
            user=request.user, author=id)
        if subscription.exists():
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'error': 'Нет подписки для удаления.'},
            status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=("get",),
        permission_classes=(IsAuthenticated,),
    )
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
