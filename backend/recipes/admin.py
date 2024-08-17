from django.contrib import admin
from import_export.admin import ImportExportMixin

from .models import (FavouriteRecipe, Ingredient, Recipe, RecipeIngredient,
                     ShoppingCart, Tag)


class RecipeIngredientAdmin(admin.StackedInline):
    model: RecipeIngredient = RecipeIngredient
    autocomplete_fields = ("ingredient",)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "author",
        "get_favorite_count",
    )
    search_fields = (
        "name",
        "author__username",
        "tags",
    )
    list_filter = (
        "name",
        "author__username",
        "tags",
    )
    inlines = (RecipeIngredientAdmin,)
    empty_value_display = "пусто"

    @admin.display(description="В избранном")
    def get_favorite_count(self, obj):
        return obj.favourite.count()


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "color", "slug")
    search_fields = ("name",)
    list_filter = ("name",)
    empty_value_display = "пусто"


@admin.register(FavouriteRecipe)
class FavoriteRecipeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "recipe")
    search_fields = ("user__username", "recipe__name")
    list_filter = ("user__username", "recipe__name")
    empty_value_display = "пусто"


@admin.register(Ingredient)
class IngridientAdmin(ImportExportMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "measurement_unit",
    )
    search_fields = (
        "name",
        "measurement_unit",
    )
    list_filter = (
        "name",
        "measurement_unit",
    )
    empty_value_display = "пусто"


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "recipe",
    )
    search_fields = (
        "user__username",
        "recipe__name",
    )
    list_filter = (
        "user__username",
        "recipe__name",
    )
    empty_value_display = "пусто"
