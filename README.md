# Yatube. Платформа для блогеров
### Описание проекта.
Проект представляет собой сервис для блогеров, где пользователям можно будет зарегистрироваться, создать и отредактировать пост, загрузить картинки, написать комментарии.  

#### Технологии.
В проекте использованы следующие технологии:
Python 3.7, Django 2.2.16, Pillow 8.3.1.

### Как запустить проект:

Клонировать репозиторий и перейти в него в командной строке:

```
git clone https://github.com/mdkostrov/hw05_final.git
```

```
cd hw05_final
```

Cоздать и активировать виртуальное окружение (для Windows):

```
python -m venv env
```

```
source venv/scripts/activate
```

Обновить установщик пакетов pip:

```
python -m pip install --upgrade pip
```

Установить зависимости из файла requirements.txt:

```
pip install -r requirements.txt
```

Выполнить миграции (для Windows):

```
python manage.py migrate
```

Запустить проект (для Windows):

```
python manage.py runserver
```
