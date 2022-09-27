from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django import forms

from posts.models import Follow, Group, Post
from posts.views import POSTS_PER_PAGE

User = get_user_model()

TEST_POSTS_COUNT = 15


class PostViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Vasya')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug'
        )
        cls.another_group = Group.objects.create(
            title='Тестовая группа2',
            slug='test-slug2'
        )
        Post.objects.bulk_create(
            Post(
                author=cls.user,
                text=f'Пост №{i}',
                id=i, group=cls.group
            ) for i in range(1, TEST_POSTS_COUNT + 1)
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_pages_use_correct_template(self):
        """URL-адрес (namespace:name) использует соответствующий шаблон."""
        post = Post.objects.get(id=1)
        reverse_names_templates = {
            reverse('posts:index'):
                'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
                'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': self.user.username}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': post.id}):
                'posts/post_detail.html',
            reverse('posts:post_create'):
                'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': post.id}):
                'posts/create_post.html'
        }
        for reverse_name, template in reverse_names_templates.items():
            with self.subTest(reverse_name=reverse_name, template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_context(self):
        """На главную страницу передается правильный контекст"""
        last_posts = (
            Post.objects.all().order_by('-pub_date')[:POSTS_PER_PAGE]
        )
        response = self.authorized_client.get(reverse('posts:index'))
        context_obj = response.context.get('page_obj').object_list
        self.assertEqual(context_obj, list(last_posts))

    def test_group_list_page_context(self):
        """На страницу группы передается правильный контекст"""
        group_posts = (
            Post.objects.filter(group=self.group)
            .order_by('-pub_date')[:POSTS_PER_PAGE]
        )
        response = (
            self.authorized_client.
            get(reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        )
        context_obj_page = response.context.get('page_obj').object_list
        context_obj_group = response.context['group']
        self.assertEqual(context_obj_page, list(group_posts))
        self.assertEqual(context_obj_group, self.group)

    def test_profile_page_context(self):
        """На страницу посты пользователя передается правильный контекст"""
        profile = (
            Post.objects.filter(author=self.user)
            .order_by('-pub_date')[:POSTS_PER_PAGE]
        )
        response = (
            self.authorized_client.
            get(reverse('posts:profile',
                kwargs={'username': (self.user.username)}))
        )
        context_obj = response.context.get('page_obj').object_list
        self.assertEqual(context_obj, list(profile))

    def test_post_detail_page_context(self):
        """
        На страницу детальной информации о
        посте передается правильный контекст
        """
        post_in_db = Post.objects.get(id=1)
        response = (
            self.authorized_client.
            get(reverse('posts:post_detail',
                kwargs={'post_id': post_in_db.id}))
        )
        post_in_context = response.context['post']
        self.assertEqual(post_in_context, post_in_db)

    def test_post_create_form_context(self):
        """На страницу создания поста передается правильный контекст формы"""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_form_context(self):
        """
        На страницу редактирования поста передается
        верный словарь контекста:
        поля формы и параметр is_edit
        """
        post = Post.objects.get(id=1)
        response = (
            self.authorized_client
            .get(reverse('posts:post_edit', kwargs={'post_id': post.id}))
        )
        context_is_edit = response.context['is_edit']
        self.assertTrue(context_is_edit)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_pages_show_correct_pagination(self):
        """Паджинация страниц работает правильно."""
        page_pagination = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        ]
        for page in page_pagination:
            response = self.authorized_client.get(page)
            self.assertEqual(
                len(response.context['page_obj']),
                POSTS_PER_PAGE
            )
            response = self.authorized_client.get(page + '?page=2')
            self.assertEqual(
                len(response.context['page_obj']),
                (TEST_POSTS_COUNT - POSTS_PER_PAGE)
            )

    def test_post_appears_correctly(self):
        """
        Пост с группой появляется на главной,
        странице группы и профайле автора, при этом пост
        не появляется на странице другой группы
        """
        post_group = Post.objects.order_by('-pub_date').first()
        pages_for_post = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        ]
        for page in pages_for_post:
            response = self.authorized_client.get(page)
            group_context = response.context['page_obj'].object_list
            self.assertIn(post_group, group_context)
        response_another_group = (
            self.authorized_client.
            get(reverse(
                'posts:group_list', kwargs={'slug': self.another_group.slug}
            ))
        )
        another_group_context = (
            response_another_group.context['page_obj'].object_list
        )
        self.assertNotIn(post_group, another_group_context)

    def test_index_cache(self):
        """
        При удалении записи из базы, она остаётся в response.content
        главной страницы до тех пор, пока кэш не будет очищен принудительно.
        """
        post = Post.objects.create(
            text='Кешированный пост',
            author=self.user
        )
        content_before = self.authorized_client.get(
            reverse('posts:index')
        ).content
        post.delete()
        content_after_delete = self.authorized_client.get(
            reverse('posts:index')
        ).content
        self.assertEqual(content_before, content_after_delete)
        cache.clear()
        content_after_cache_clear = self.authorized_client.get(
            reverse('posts:index')
        ).content
        self.assertNotEqual(content_before, content_after_cache_clear)


class FollowingTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='Автор')
        cls.follower = User.objects.create_user(username='Подписчик')

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.follower)
        self.client_author = Client()
        self.client_author.force_login(self.author)

    def test_authorized_follow_unfollow(self):
        """
        Авторизованный пользователь может подписываться на других
        пользователей и удалять их из подписок.
        """
        follow_count = Follow.objects.count()
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author.username}
            )
        )
        follow_object = Follow.objects.first()
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        self.assertEqual(follow_object.author, self.author)
        self.assertEqual(follow_object.user, self.follower)
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.author.username}
            )
        )
        self.assertEqual(Follow.objects.count(), follow_count)
        self.assertFalse(
            Follow.objects.filter(
                user=self.follower,
                author=self.author
            ).exists()
        )

    def test_post_for_followers(self):
        """
        Новая запись пользователя появляется в ленте тех,
        кто на него подписан и не появляется в ленте тех, кто не подписан.
        """
        follow_obj = Follow.objects.create(
            author=self.author,
            user=self.follower
        )
        post = Post.objects.create(
            author=self.author,
            text="Лайк подписка репост"
        )
        response_before = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertIn(post, response_before.context['page_obj'].object_list)
        follow_obj.delete()
        response_after = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertNotIn(post, response_after.context['page_obj'].object_list)
