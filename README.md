# Cao AI 图生视频工作台

Vue 3 + Django 的图生视频首版原型。前端提供商品图上传、厂商选择、参数填写、任务轮询和结果预览；后端保存任务并通过 provider 抽象接入火山 Seedance 与阿里万相。

## 开发启动

```powershell
.\.venv\Scripts\activate
cd backend
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

另开一个终端：

```powershell
cd "E:\CodexProject\Cao AI\frontend"
npm install
npm run dev
```

前端默认访问 `http://127.0.0.1:8000/api`。如需修改：

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000/api"
```

## 环境变量

复制 `.env.example` 为 `.env`。开发阶段可先开启 mock：

```env
VIDEO_PROVIDER_FORCE_MOCK=true
```

接真实厂商时改为 `false`，并填写火山或阿里密钥。

## 验证

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py test videos

cd ..\frontend
npm test
npm run build
```
