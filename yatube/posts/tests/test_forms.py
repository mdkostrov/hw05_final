import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateEditFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user_author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
            id='1',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def tearDown(self):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_post_creation_form(self):
        """
        При отправке валидной формы со страницы создания
        поста создаётся новая запись в базе данных.
        """
        posts_count = Post.objects.count()
        small_gif = (
             b'\x47\x49\x46\x38\x39\x61\x02\x00'
             b'\x01\x00\x80\x00\x00\x00\x00\x00'
             b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
             b'\x00\x00\x00\x2C\x00\x00\x00\x00'
             b'\x02\x00\x01\x00\x00\x02\x02\x0C'
             b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif',
        )
        form_data = {
            'text': 'Новый тестовый текст',
            'author': self.user,
            'image': uploaded
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse(
                'posts:profile', kwargs={'username': self.user.username}
            )
        )
        last_post = Post.objects.first()
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Новый тестовый текст',
            ).exists()
        )
        self.assertEqual(last_post.text, 'Новый тестовый текст')
        self.assertEqual(last_post.group, None)
        self.assertEqual(last_post.author, self.user)
        self.assertEqual(last_post.image.name, 'posts/small.gif')

    def test_post_edit_form(self):
        """
        При отправке валидной формы со страницы
        редактирования поста происходит изменение
        поста с post_id в базе данных.
        """
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Измененный тестовый текст',
            'group': '',
        }
        response_post_edit = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        edited_post = Post.objects.filter(text='Измененный тестовый текст')
        response_group_list = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        old_group_context = response_group_list.context['page_obj'].object_list
        self.assertRedirects(
            response_post_edit, reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id}
            )
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(
            Post.objects.filter(
                text='Измененный тестовый текст',
                id='1'
            ).exists()
        )
        self.assertFalse(
            Post.objects.filter(
                text='Тестовый текст',
                id='1'
            ).exists()
        )
        self.assertNotIn(edited_post, old_group_context)

    def test_image_context(self):
        """
        Проверяет, что при выводе поста с картинкой
        изображение передаётся в словаре context
        """
        small_gif = (
             b'\x47\x49\x46\x38\x39\x61\x02\x00'
             b'\x01\x00\x80\x00\x00\x00\x00\x00'
             b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
             b'\x00\x00\x00\x2C\x00\x00\x00\x00'
             b'\x02\x00\x01\x00\x00\x02\x02\x0C'
             b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif',
        )
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        last_post = Post.objects.first()
        pages_with_image_context = {
            reverse('posts:index'): 'page_obj',
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): 'page_obj',
            reverse(
                'posts:profile', kwargs={'username': self.user.username}
            ): 'page_obj',
        }
        for page, context in pages_with_image_context.items():
            with self.subTest(page=page, context=context):
                response = self.authorized_client.get(page)
                post_image_context = (
                    response.context.get(context).object_list[0].image
                )
                self.assertEqual(last_post.image, post_image_context)
        response_post_detail = self.authorized_client.get(
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id}
            )
        )
        post_detail_img = (
            response_post_detail.context.get('post').image
        )
        self.assertEqual(self.post.image, post_detail_img)

    def test_authorized_comment_post(self):
        """
        Проверка добавления комментария
        авторизованным пользователем.
        """
        comments_count = Comment.objects.count()
        post = Post.objects.last()
        form_data = {'text': 'Тестовый комментарий'}
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': post.id}
            ),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse(
                'posts:post_detail',
                kwargs={'post_id': post.id}
            )
        )
        comment = Comment.objects.last()
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertEqual(comment.text, 'Тестовый комментарий')
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.post.id, post.id)

    def test_guest_comment_post(self):
        """
        Проверка невозможности добавления
        комментария неавторизованным пользователем.
        """
        comments_count = Comment.objects.count()
        post = Post.objects.last()
        form_data = {'text': 'Тестовый комментарий гостя'}
        response = self.guest_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': post.id}
            ),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count)
        self.assertRedirects(
            response,
            reverse('users:login') +
            '?next=' +
            reverse('posts:add_comment',
                    kwargs={'post_id': post.id})
        )
