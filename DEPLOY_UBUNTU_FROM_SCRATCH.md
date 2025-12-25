# Развёртывание `speech-analyzer-api` на Ubuntu “с нуля” (NVIDIA + CUDA + Docker + Python 3.12 + nginx + supervisor)

Ниже — практическая пошаговая инструкция для чистого сервера Ubuntu. Команды рассчитаны на запуск от пользователя с `sudo`.

> Важно: в шаблонах из `setup/` у вас есть плейсхолдеры вида `<имя-пользователя>` — их нужно заменить на реального Linux-пользователя (например `sa-admin`).

---

## 0) Переменные (подставьте свои)

```bash
export APP_USER="sa-admin"
export APP_HOME="/home/${APP_USER}"
export APP_DIR="${APP_HOME}/speech-analyzer-api"
export DOMAIN="ssa.ai-check.ru"   # замените на свой домен/адрес
```

Создайте пользователя (если ещё нет):

```bash
sudo adduser --disabled-password --gecos "" "${APP_USER}"
sudo usermod -aG sudo "${APP_USER}"
```

---

## 1) Обновление системы и базовые пакеты

```bash
sudo apt update
sudo apt -y upgrade
sudo apt -y install git curl wget ca-certificates gnupg lsb-release unzip build-essential
```

---

## 2) Установка драйверов NVIDIA и CUDA

### 2.1 Проверка, что GPU виден

```bash
lspci | grep -i nvidia || true
```

### 2.2 Драйвер NVIDIA (рекомендованный)

```bash
sudo apt -y install ubuntu-drivers-common
sudo ubuntu-drivers autoinstall
sudo reboot
```

После перезагрузки:

```bash
nvidia-smi
```

### 2.3 CUDA Toolkit (если нужно для вашего ML-стека)

Способ зависит от версии Ubuntu и требований вашей модели. Универсальный путь — поставить CUDA из официального репозитория NVIDIA.

1) Добавьте репозиторий CUDA (пример для Ubuntu 22.04; для 24.04 меняется `ubuntu2204` → `ubuntu2404`):

```bash
distribution="ubuntu2204"
curl -fsSL "https://developer.download.nvidia.com/compute/cuda/repos/${distribution}/x86_64/3bf863cc.pub" | sudo gpg --dearmor -o /usr/share/keyrings/cuda-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/cuda-archive-keyring.gpg] https://developer.download.nvidia.com/compute/cuda/repos/${distribution}/x86_64/ /" | sudo tee /etc/apt/sources.list.d/cuda.list >/dev/null
sudo apt update
```

2) Установите toolkit (пример: “дефолтный” metapackage):

```bash
sudo apt -y install cuda-toolkit
```

3) Проверка:

```bash
nvcc --version || true
nvidia-smi
```

---

## 3) Установка FFmpeg

FFmpeg нужен для обработки/конвертации аудио.

```bash
sudo apt update
sudo apt -y install ffmpeg
ffmpeg -version
```

---

## 4) Установка Certbot (Let’s Encrypt)

Certbot нужен для выпуска/обновления TLS-сертификатов, которые использует ваш nginx-конфиг `setup/sa`.

```bash
sudo apt update
sudo apt -y install certbot python3-certbot-nginx
certbot --version
```

Выпуск сертификата (после того как DNS `DOMAIN` указывает на сервер, а 80/443 порты открыты):

```bash
sudo certbot --nginx -d "${DOMAIN}"
```

Проверка автообновления:

```bash
sudo systemctl status certbot.timer --no-pager || true
sudo certbot renew --dry-run
```

---

## 5) Установка Docker и Compose (plugin)

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

sudo apt update
sudo apt -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "${APP_USER}"
```

Перелогиньтесь под пользователем (или `newgrp docker`), чтобы работали команды `docker` без `sudo`.

---

## 6) Установка Python 3.12 и venv

### Вариант A (Ubuntu 24.04+)

```bash
sudo apt -y install python3.12 python3.12-venv python3.12-dev
```

### Вариант B (Ubuntu 22.04: через deadsnakes PPA)

```bash
sudo apt -y install software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt -y install python3.12 python3.12-venv python3.12-dev
```

Установим свежий pip:

```bash
python3.12 -m ensurepip --upgrade
python3.12 -m pip install -U pip wheel setuptools
```

---

## 7) Клонирование проекта из GitHub и подготовка окружения

Переключитесь на пользователя приложения:

```bash
sudo -iu "${APP_USER}"
```

Клонируйте репозиторий:

```bash
cd "${APP_HOME}"
git clone <SSH_ИЛИ_HTTPS_URL_ВАШЕГО_REPO> speech-analyzer-api
cd "${APP_DIR}"
```

Создайте `.env` (переменные используются в `docker-compose.db.yml` и обычно в приложении):

```bash
cp env.example .env
nano .env
```

Минимально убедитесь, что в `.env` заданы:
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`

---

## 8) Создание виртуального окружения, активация, зависимости

```bash
cd "${APP_DIR}"
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip wheel setuptools
pip install -r requirements.txt
```

---

## 9) Запуск БД (docker-compose.db.yml)

Из каталога проекта:

```bash
cd "${APP_DIR}"
set -a
source .env
set +a

docker compose -f docker-compose.db.yml up -d
docker compose -f docker-compose.db.yml ps
```

Проверка готовности:

```bash
docker compose -f docker-compose.db.yml logs -n 200 postgres
```

---

## 10) Подготовка каталогов под socket/logs (требуется для ваших шаблонов)

В `setup/gunicorn_start` bind идёт в `unix:$DIR/run/gunicorn.sock`, а supervisor пишет лог в `logs/…`.

```bash
cd "${APP_DIR}"
mkdir -p run logs
chmod 755 run logs
```

Скопируйте и сделайте скрипт запуска исполняемым:

```bash
sudo cp "${APP_DIR}/setup/sa.conf" "${APP_DIR}/sa.conf"
chmod +x "${APP_DIR}/gunicorn_start"
```

---

## 11) Настройка supervisor (используем `setup/sa.conf` и `setup/gunicorn_start`)

Установите supervisor:

```bash
sudo apt -y install supervisor
sudo systemctl enable --now supervisor
```

Скопируйте и отредактируйте конфиг:

```bash
sudo cp "${APP_DIR}/setup/sa.conf" /etc/supervisor/conf.d/speech-analyzer-api.conf
sudo nano /etc/supervisor/conf.d/speech-analyzer-api.conf
```

В файле `/etc/supervisor/conf.d/speech-analyzer-api.conf` замените:
- `command=/home/<имя-пользователя>/speech-analyzer-api/gunicorn_start` → на **ваш путь** к скрипту
- `user=<имя-пользователя>` → на **ваш пользователя**, например `${APP_USER}`
- `stdout_logfile=/home/<имя-пользователя>/speech-analyzer-api/logs/gunicorn-error.log` → на **ваш путь** к логам


Перечитать конфиги supervisor и запустить:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start speech-analyzer-api
sudo supervisorctl status
```

---

## 12) nginx: установка и подключение конфига из `setup/sa`

Установка:

```bash
sudo apt -y install nginx
sudo systemctl enable --now nginx
```

Скопируйте конфиг:

```bash
sudo cp "${APP_DIR}/setup/sa" /etc/nginx/sites-available/sa
sudo nano /etc/nginx/sites-available/sa
```

Что нужно заменить/проверить в `/etc/nginx/sites-available/sa`:
- `server_name ssa.ai-check.ru;` → **ваш домен/адрес**
- пути сертификатов Let’s Encrypt (`/etc/letsencrypt/live/...`) → **ваши** (или временно уберите https-блок и оставьте только `listen 80;`)
- `proxy_pass http://127.0.0.1:8000;` → **если у вас приложение реально слушает 8000 TCP**.  
- `alias /home/sa-admin/speech-analyzer-api/speech-data/;` → привести к **реальному пути** на сервере (обычно это `${APP_DIR}/speech-data/`)


Включите сайт и перезагрузите nginx:

```bash
sudo ln -sf /etc/nginx/sites-available/sa /etc/nginx/sites-enabled/sa
sudo nginx -t
sudo systemctl reload nginx
```

---

## 13) Финальный запуск/проверка

Проверьте статус supervisor и сокет:

```bash
sudo supervisorctl status
ls -la "${APP_DIR}/run/gunicorn.sock" || true
```

Проверьте nginx:

```bash
sudo systemctl status nginx --no-pager
sudo tail -n 200 /var/log/nginx/error.log || true
```

Проверка API (локально на сервере):

```bash
curl -i http://127.0.0.1/api/v1/health || true
curl -i http://127.0.0.1/docs || true
```

---

