from django import forms

from .models import Comment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        help_texts = {
            'group': ('Выберите группу (необязательно)'),
            'text': ('Введите текст поста'),
            'image': ('Добавить изображение (необязательно)')
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        help_texts = {
            'text': ('Оставьте комментарий...')
        }
