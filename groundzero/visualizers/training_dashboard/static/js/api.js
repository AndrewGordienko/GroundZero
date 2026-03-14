export const API = {
    async getStatus() {
        try {
            const response = await fetch('/api/status');
            return await response.json();
        } catch (e) {
            console.warn("API Sync: Waiting for server...");
            return null;
        }
    }
};