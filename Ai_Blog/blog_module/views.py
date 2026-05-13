# blog_module/views.py
from django.db.models import F
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Post, Comment, Tag, Like
from .forms import PostForm, CommentForm


# لیست پست‌ها (Homepage) - نیاز به login
class PostListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = 'blog_module/post_list.html'
    context_object_name = 'posts'
    ordering = ['-created_at']
    paginate_by = 10
    login_url = 'account:login'

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related('likes', 'tags', 'author')
        tag_slug = self.request.GET.get('tag')
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tags'] = Tag.objects.all()
        context['selected_tag'] = self.request.GET.get('tag')
        return context


# جزئیات پست - نیاز به login
class PostDetailView(LoginRequiredMixin, DetailView):
    model = Post
    template_name = 'blog_module/post_detail.html'
    context_object_name = 'post'
    login_url = 'account:login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comments'] = self.object.comments.filter(parent=None).order_by('-created_at')
        context['comment_form'] = CommentForm()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        comment_form = CommentForm(request.POST)

        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = self.object
            comment.user = request.user

            parent_id = request.POST.get('parent_id')
            if parent_id:
                comment.parent = get_object_or_404(Comment, id=parent_id)

            comment.save()
            self.object.comment_count += 1
            self.object.save()
            messages.success(request, 'Comment added successfully!')
            return redirect('blog:post_detail', slug=self.object.slug)

        return self.render_to_response(self.get_context_data(comment_form=comment_form))


# ساخت پست - نیاز به login
class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog_module/post_form.html'
    login_url = 'account:login'

    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, 'Post created successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('blog:post_detail', kwargs={'slug': self.object.slug})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        return context


# ویرایش پست - نیاز به login و مالکیت
class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog_module/post_form.html'
    login_url = 'account:login'

    def test_func(self):
        post = self.get_object()
        return post.author == self.request.user

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect('account:login')
        messages.error(self.request, 'You can only edit your own posts.')
        return redirect('blog:post_detail', slug=self.get_object().slug)

    def form_valid(self, form):
        messages.success(self.request, 'Post updated successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('blog:post_detail', kwargs={'slug': self.object.slug})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Edit'
        return context


# حذف پست - نیاز به login و مالکیت
class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    success_url = reverse_lazy('blog:post_list')
    login_url = 'account:login'

    def test_func(self):
        post = self.get_object()
        return post.author == self.request.user

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect('account:login')
        messages.error(self.request, 'You can only delete your own posts.')
        return redirect('blog:post_detail', slug=self.get_object().slug)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Post deleted successfully!')
        return super().delete(request, *args, **kwargs)


@login_required
@require_POST
def toggle_like(request, slug):
    post = get_object_or_404(Post, slug=slug)
    like, created = Like.objects.get_or_create(post=post, user=request.user)

    if not created:
        like.delete()
        Post.objects.filter(slug=slug).update(like_count=F('like_count') - 1)
        liked = False
    else:
        Post.objects.filter(slug=slug).update(like_count=F('like_count') + 1)
        liked = True

    post.refresh_from_db()

    return JsonResponse({
        'status': 'success',  # ✅ این خط رو اضافه کن
        'liked': liked,
        'like_count': post.like_count
    })


@login_required
@require_POST
def add_comment(request, slug):
    post = get_object_or_404(Post, slug=slug)
    content = request.POST.get('content', '').strip()
    parent_id = request.POST.get('parent_id')

    if not content:
        return JsonResponse({'error': 'محتوای کامنت نمی‌تونه خالی باشه'}, status=400)

    parent = None
    if parent_id:
        parent = get_object_or_404(Comment, id=parent_id, post=post)

    comment = Comment.objects.create(
        post=post,
        author=request.user,
        content=content,
        parent=parent
    )

    # آپدیت تعداد کامنت‌ها
    post.comment_count = F('comment_count') + 1
    post.save(update_fields=['comment_count'])

    return JsonResponse({
        'success': True,
        'comment': {
            'id': comment.id,
            'author': comment.author.username,
            'author_avatar': comment.author.avatar.url if comment.author.avatar else f"https://api.dicebear.com/7.x/initials/svg?seed={comment.author.username}",
            'content': comment.content,
            'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M'),
            'parent_id': parent.id if parent else None
        }
    })