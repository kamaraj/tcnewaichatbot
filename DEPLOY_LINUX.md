# Deploying TCBot on Linux

This guide covers deploying the FastAPI backend and the React Native Web frontend on a Linux server (e.g., Ubuntu/Debian).

## 1. Backend Deployment (Docker)

The easiest way to run the backend on Linux is using Docker.

### Prerequisites
- Docker & Docker Compose installed on the Linux server.
- [Ollama](https://ollama.com) installed and running on the host (or inside a container with GPU support).

### Steps
1. **Copy the code** to your server:
   ```bash
   scp -r TCBot user@your-linux-server:/path/to/app
   ```
2. **Setup Environment**:
   Edit `.env` if needed (e.g., set `OLLAMA_BASE_URL` to `http://host.docker.internal:11434` or the host IP).
3. **Run services**:
   ```bash
   cd TCBot
   docker-compose up -d --build
   ```
4. **Verify**:
   Check `http://your-server-ip:8000/docs`.

---

## 2. Frontend Deployment (Web Interface)

Since React Native Expo creates mobile apps, for Linux "deployment" we typically mean the **Web version**.

### Prerequisites
- Node.js (v18+) installed on the server.

### Steps
1. **Navigate to frontend**:
   ```bash
   cd frontend
   ```
2. **Install Dependencies**:
   ```bash
   npm install
   ```
3. **Configure API URL**:
   Edit `api/client.js` and set the `BASE_URL` to your Linux server's IP:
   ```javascript
   const BASE_URL = 'http://your-server-ip:8000/api/v1';
   ```
4. **Build for Web**:
   ```bash
   npx expo export -p web
   ```
   This creates a `dist` directory with static files.
5. **Serve the Static Site**:
   You can serve the `dist` folder using any web server (Nginx, Apache, or `serve`).
   ```bash
   # Quick test using 'serve'
   npx serve dist -p 3000
   ```
   Now access the app at `http://your-server-ip:3000`.

---

## 3. Alternative: Running locally for Development
If you just want to run it on a Linux desktop for development:
1. Terminal 1 (Backend): `./run_local.sh`
2. Terminal 2 (Frontend):
   ```bash
   cd frontend
   npm install
   npx expo start --web
   ```
