from django.contrib import admin
from .models import Tag, Post, Comment, Like


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at', 'like_count', 'comment_count')
    list_filter = ('created_at', 'updated_at', 'tags')
    search_fields = ('title', 'content', 'excerpt')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('tags',)
    readonly_fields = ('created_at', 'updated_at', 'like_count', 'comment_count')

    fieldsets = (
        ('Basic Info', {
            'fields': ('author', 'title', 'slug', 'excerpt')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Tags & AI', {
            'fields': ('tags', 'ai_tags')
        }),
        ('Stats', {
            'fields': ('like_count', 'comment_count', 'created_at', 'updated_at')
        }),
    )


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'created_at', 'parent')
    list_filter = ('created_at',)
    search_fields = ('content', 'author__username', 'post__title')
    raw_id_fields = ('post', 'author', 'parent')

