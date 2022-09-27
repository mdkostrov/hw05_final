from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from posts.models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
        )
        Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
            id='1'
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='TestName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.client_author = Client()
        self.client_author.force_login(self.author)

    def test_urls_exist_at_desired_location(self):
        """
        Тест доступности страниц для
        неавторизованного/авторизованного
        пользователя и автора поста
        """
        urls_clients_statuses = [
            ['/', self.authorized_client, HTTPStatus.OK],
            ['/', self.guest_client, HTTPStatus.OK],
            ['/create/', self.authorized_client, HTTPStatus.OK],
            ['/create/', self.guest_client, HTTPStatus.FOUND],
            ['/group/test-slug/', self.authorized_client, HTTPStatus.OK],
            ['/group/test-slug/', self.guest_client, HTTPStatus.OK],
            ['/profile/author/', self.authorized_client, HTTPStatus.OK],
            ['/profile/author/', self.guest_client, HTTPStatus.OK],
            ['/posts/1/', self.authorized_client, HTTPStatus.OK],
            ['/posts/1/', self.guest_client, HTTPStatus.OK],
            ['/posts/1/edit/', self.authorized_client, HTTPStatus.FOUND],
            ['/posts/1/edit/', self.guest_client, HTTPStatus.FOUND],
            ['/posts/1/edit/', self.client_author, HTTPStatus.OK],
            ['/unexisting/', self.guest_client, HTTPStatus.NOT_FOUND],
        ]
        for address, client, status in urls_clients_statuses:
            with self.subTest(address=address, client=client, status=status):
                response = client.get(address)
                self.assertEqual(response.status_code, status)

    def test_url_redirects_anonymous_client(self):
        """
        Проверка перенаправления неавторизованного
        пользователя на страницу авторизации
        """
        urls_list = [
            '/create/',
            '/posts/1/edit/'
        ]
        for address in urls_list:
            with self.subTest(address=address):
                response = self.guest_client.get(address, follow=True)
                self.assertRedirects(
                    response, f'/auth/login/?next={address}'
                )

    def test_urls_use_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        url_templates_names = {
            '/': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/profile/author/': 'posts/profile.html',
            '/posts/1/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            '/posts/1/edit/': 'posts/create_post.html',
        }
        for address, template in url_templates_names.items():
            with self.subTest(address=address):
                response = self.client_author.get(address)
                self.assertTemplateUsed(response, template)
