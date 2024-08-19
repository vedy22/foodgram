from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from recipes.models import (FavouriteRecipe, Ingredient, Recipe,
                            RecipeIngredient, ShoppingCart, Tag)
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from users.models import Follow

from .fields import Base64ImageField
from .serializers_mixins import IsAuthAndExistsMixin

User = get_user_model()


class CustomUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_subscribed",
        )

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return Follow.objects.filter(
                user=request.user, author=obj
            ).exists()
        return False


class CustomUserCreateSerializer(UserCreateSerializer):
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    email = serializers.EmailField(required=True, max_length=254)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
        )

    def validate(self, attrs):
        if User.objects.filter(email=attrs["email"]).exists():
            raise ValidationError(
                "Пользователь с таким email уже существует.",
            )
        return super().validate(attrs)


class TagsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = (
            "id",
            "name",
            "color",
            "slug",
        )


class IngredientsRecipeSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(
        source="ingredient.measurement_unit"
    )
    id = serializers.ReadOnlyField(source="ingredient.id")

    class Meta:
        model = RecipeIngredient
        fields = ("id", "name", "measurement_unit", "amount")


class SubscriptionSerializer(CustomUserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_subscribed",
            "recipes",
            "recipes_count",
        )

    @staticmethod
    def get_resipe_serializer():
        return ShortRecipeSerializer

    def get_recipes(self, object):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        recipes = object.recipes.all()
        if limit:
            recipes = recipes[:int(limit)]
        serializer = ShortRecipeSerializer(
            recipes,
            many=True,
            read_only=True,
        )
        return serializer.data

    @staticmethod
    def get_recipes_count(obj):
        return Recipe.objects.filter(author=obj).count()


class CreateSubscribeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = ("user", "author")

    def validate(self, data):
        if self.context['request'].method == 'POST':
            if self.context['request'].user == data['author']:
                raise ValidationError(
                    detail='Нельзя подписаться на себя.',
                    code=status.HTTP_400_BAD_REQUEST
                )
            if Follow.objects.filter(
                    user=self.context['request'].user,
                    author=data['author']).exists():
                raise ValidationError(
                    detail='Вы уже подписаны',
                    code=status.HTTP_400_BAD_REQUEST
                )
        return data


class RecipeCreateIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        source="ingredient",
        queryset=Ingredient.objects.all(),
    )

    class Meta:
        model = RecipeIngredient
        fields = ("id", "amount")


class RecipeWriteSerializer(serializers.ModelSerializer, IsAuthAndExistsMixin):
    ingredients = RecipeCreateIngredientSerializer(many=True)
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    author = CustomUserSerializer(required=False)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )
        read_only_fields = ("author",)

    def get_is_favorited(self, obj):
        return self.is_auth_and_exists(obj, FavouriteRecipe)

    def get_is_in_shopping_cart(self, obj):
        return self.is_auth_and_exists(obj, ShoppingCart)

    @staticmethod
    def validate_ingredients(values):
        if not values:
            raise serializers.ValidationError(
                "Необходимо указать хотя бы один ингредиент.",
            )
        ingredients_list = []
        for value in values:
            ingredient = (get_object_or_404
                          (Ingredient, id=value["ingredient"].id)
                          )
            if int(value["amount"]) <= 0:
                raise (
                    serializers.ValidationError({"Вес должен быть больше 0."})
                )
            if ingredient in ingredients_list:
                raise serializers.ValidationError(
                    "Ингредиенты должны быть уникальными."
                )
            ingredients_list.append(ingredient)
        return values

    @staticmethod
    def validate_tags(values):
        if not values:
            raise (
                serializers.ValidationError
                ("Необходимо выбрать хотя бы один тег.")
            )
        tags_list = []
        for tag in values:
            if tag in tags_list:
                raise (
                    serializers.ValidationError
                    ("Теги должны быть уникальными.")
                )
            tags_list.append(tag)
        return values

    @staticmethod
    def ingredients_and_tags(validated_data):
        ingredients = validated_data.pop("ingredients", None)
        tags = validated_data.pop("tags", None)
        return ingredients, tags

    @staticmethod
    def ingredients_create(ingredients, obj):
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=obj,
                ingredient_id=ingredient["ingredient"].id,
                amount=ingredient["amount"],
            )
            for ingredient in ingredients
        ])

    def create(self, validated_data):
        ingredients, tags = self.ingredients_and_tags(validated_data)
        obj = Recipe.objects.create(**validated_data)
        obj.tags.set(tags)
        self.ingredients_create(ingredients, obj)
        return obj

    def update(self, instance, validated_data):
        ingredients, tags = self.ingredients_and_tags(validated_data)
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.ingredients_create(ingredients, instance)
        return super().update(instance, validated_data)

    def validate(self, data):
        if "ingredients" not in data:
            raise ValidationError(
                detail="Необходимо указать ингредиенты.",
                code=status.HTTP_400_BAD_REQUEST
            )
        if "tags" not in data:
            raise ValidationError(
                detail="Необходимо указать теги.",
                code=status.HTTP_400_BAD_REQUEST
            )
        return data

    def to_representation(self, instance):
        return RecipeReadSerializer(
            instance, context={"request": self.context.get("request")}
        ).data


class RecipeReadSerializer(serializers.ModelSerializer, IsAuthAndExistsMixin):
    image = Base64ImageField()
    tags = TagsSerializer(many=True, read_only=True)
    author = CustomUserSerializer(
        read_only=True,
    )
    ingredients = (
        IngredientsRecipeSerializer
        (many=True, source="recipe_ingredients")
    )
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe
        exclude = ("pub_date",)

    def get_is_favorited(self, obj):
        return self.is_auth_and_exists(obj, FavouriteRecipe)

    def get_is_in_shopping_cart(self, obj):
        return self.is_auth_and_exists(obj, ShoppingCart)


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model: Ingredient = Ingredient
        fields = ("id", "name", "measurement_unit")


class ShortRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")
