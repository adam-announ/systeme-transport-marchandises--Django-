// static/js/realtime.js

// Configuration WebSocket
class TransportWebSocket {
    constructor(type, params = {}) {
        this.type = type;
        this.params = params;
        this.socket = null;
        this.reconnectInterval = 5000;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        let url;

        switch (this.type) {
            case 'tracking':
                url = `${protocol}//${window.location.host}/ws/tracking/${this.params.missionId}/`;
                break;
            case 'dashboard':
                url = `${protocol}//${window.location.host}/ws/dashboard/`;
                break;
            case 'notifications':
                url = `${protocol}//${window.location.host}/ws/notifications/`;
                break;
            default:
                console.error('Type WebSocket non supporté');
                return;
        }

        this.socket = new WebSocket(url);

        this.socket.onopen = (e) => {
            console.log('WebSocket connecté');
            this.reconnectAttempts = 0;
            if (this.onOpen) this.onOpen(e);
        };

        this.socket.onmessage = (e) => {
            const data = JSON.parse(e.data);
            this.handleMessage(data);
        };

        this.socket.onclose = (e) => {
            console.log('WebSocket déconnecté');
            if (this.onClose) this.onClose(e);
            this.attemptReconnect();
        };

        this.socket.onerror = (e) => {
            console.error('Erreur WebSocket:', e);
            if (this.onError) this.onError(e);
        };
    }

    handleMessage(data) {
        switch (data.type) {
            case 'position':
                if (this.onPositionUpdate) this.onPositionUpdate(data.data);
                break;
            case 'status':
                if (this.onStatusUpdate) this.onStatusUpdate(data.data);
                break;
            case 'incident':
                if (this.onIncident) this.onIncident(data.data);
                break;
            case 'stats_update':
                if (this.onStatsUpdate) this.onStatsUpdate(data.data);
                break;
            case 'new_notification':
                if (this.onNewNotification) this.onNewNotification(data.data);
                break;
            case 'error':
                console.error('Erreur serveur:', data.message);
                break;
        }
    }

    send(data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(data));
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                console.log(`Tentative de reconnexion ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
                this.connect();
            }, this.reconnectInterval);
        }
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }
}

// Suivi en temps réel sur carte
class LiveTrackingMap {
    constructor(mapElementId, missionId) {
        this.mapElementId = mapElementId;
        this.missionId = missionId;
        this.map = null;
        this.markers = {};
        this.route = null;
        this.ws = null;
    }

    async init() {
        // Initialiser la carte Google Maps
        this.map = new google.maps.Map(document.getElementById(this.mapElementId), {
            zoom: 13,
            center: { lat: 33.5731, lng: -7.5898 }, // Casablanca par défaut
            mapTypeId: 'roadmap',
            styles: this.getMapStyles()
        });

        // Charger les données de la mission
        await this.loadMissionData();

        // Connecter WebSocket
        this.connectWebSocket();
    }

    async loadMissionData() {
        try {
            const response = await fetch(`/api/mission/${this.missionId}/`);
            const data = await response.json();

            // Ajouter marqueur de départ
            this.addMarker('pickup', {
                lat: data.pickup_lat,
                lng: data.pickup_lng
            }, 'Enlèvement', 'green');

            // Ajouter marqueur de destination
            this.addMarker('delivery', {
                lat: data.delivery_lat,
                lng: data.delivery_lng
            }, 'Livraison', 'red');

            // Tracer l'itinéraire
            if (data.route) {
                this.drawRoute(data.route);
            }

            // Centrer la carte
            this.fitBounds();

        } catch (error) {
            console.error('Erreur chargement mission:', error);
        }
    }

    connectWebSocket() {
        this.ws = new TransportWebSocket('tracking', { missionId: this.missionId });

        this.ws.onPositionUpdate = (data) => {
            this.updateTransporterPosition(data);
        };

        this.ws.onStatusUpdate = (data) => {
            this.updateStatus(data);
        };

        this.ws.onIncident = (data) => {
            this.showIncident(data);
        };

        this.ws.connect();
    }

    updateTransporterPosition(data) {
        const position = { lat: data.lat, lng: data.lon };

        if (this.markers.transporter) {
            // Animer le déplacement
            this.animateMarker(this.markers.transporter, position);
        } else {
            // Créer le marqueur
            this.addMarker('transporter', position, 'Transporteur', 'blue', {
                icon: '/static/images/truck-icon.png'
            });
        }

        // Mettre à jour les infos
        if (data.speed) {
            this.updateInfoPanel({
                speed: data.speed,
                heading: data.heading,
                timestamp: data.timestamp
            });
        }
    }

    addMarker(id, position, title, color, options = {}) {
        const marker = new google.maps.Marker({
            position: position,
            map: this.map,
            title: title,
            icon: options.icon || this.getMarkerIcon(color),
            ...options
        });

        this.markers[id] = marker;

        // Ajouter info window
        const infoWindow = new google.maps.InfoWindow({
            content: `<div><strong>${title}</strong></div>`
        });

        marker.addListener('click', () => {
            infoWindow.open(this.map, marker);
        });
    }

    animateMarker(marker, newPosition) {
        const startPosition = marker.getPosition();
        const endPosition = new google.maps.LatLng(newPosition.lat, newPosition.lng);
        
        let progress = 0;
        const animation = setInterval(() => {
            progress += 0.02;
            if (progress > 1) {
                clearInterval(animation);
                return;
            }

            const lat = startPosition.lat() + (endPosition.lat() - startPosition.lat()) * progress;
            const lng = startPosition.lng() + (endPosition.lng() - startPosition.lng()) * progress;
            
            marker.setPosition(new google.maps.LatLng(lat, lng));
        }, 10);
    }

    drawRoute(routeData) {
        // Décoder la polyline
        const path = google.maps.geometry.encoding.decodePath(routeData.polyline);

        this.route = new google.maps.Polyline({
            path: path,
            geodesic: true,
            strokeColor: '#2196F3',
            strokeOpacity: 0.8,
            strokeWeight: 4
        });

        this.route.setMap(this.map);
    }

    fitBounds() {
        const bounds = new google.maps.LatLngBounds();
        
        Object.values(this.markers).forEach(marker => {
            bounds.extend(marker.getPosition());
        });

        this.map.fitBounds(bounds);
    }

    getMarkerIcon(color) {
        return {
            path: google.maps.SymbolPath.CIRCLE,
            fillColor: color,
            fillOpacity: 0.8,
            strokeColor: 'white',
            strokeWeight: 2,
            scale: 8
        };
    }

    getMapStyles() {
        // Style de carte personnalisé
        return [
            {
                featureType: 'transit',
                elementType: 'labels.icon',
                stylers: [{ visibility: 'off' }]
            }
        ];
    }

    updateInfoPanel(info) {
        const panel = document.getElementById('tracking-info');
        if (panel) {
            panel.innerHTML = `
                <div class="info-item">
                    <span>Vitesse:</span> ${info.speed} km/h
                </div>
                <div class="info-item">
                    <span>Direction:</span> ${info.heading}°
                </div>
                <div class="info-item">
                    <span>Dernière MAJ:</span> ${new Date(info.timestamp).toLocaleTimeString()}
                </div>
            `;
        }
    }

    updateStatus(data) {
        const statusElement = document.getElementById('mission-status');
        if (statusElement) {
            statusElement.textContent = data.status;
            statusElement.className = `status-badge status-${data.status.toLowerCase()}`;
        }
    }

    showIncident(data) {
        // Afficher une alerte
        const alert = document.createElement('div');
        alert.className = 'alert alert-warning';
        alert.innerHTML = `
            <strong>Incident signalé:</strong> ${data.incident_type} - ${data.description}
        `;
        
        document.getElementById('alerts-container').appendChild(alert);

        // Ajouter un marqueur sur la carte
        if (this.markers.transporter) {
            const position = this.markers.transporter.getPosition();
            this.addMarker(`incident_${Date.now()}`, {
                lat: position.lat(),
                lng: position.lng()
            }, 'Incident', 'orange');
        }
    }

    destroy() {
        if (this.ws) {
            this.ws.disconnect();
        }
    }
}

// Dashboard temps réel
class RealtimeDashboard {
    constructor() {
        this.ws = null;
        this.charts = {};
    }

    init() {
        this.connectWebSocket();
        this.initCharts();
        this.startAutoRefresh();
    }

    connectWebSocket() {
        this.ws = new TransportWebSocket('dashboard');

        this.ws.onStatsUpdate = (data) => {
            this.updateStats(data);
            this.updateCharts(data);
        };

        this.ws.connect();
    }

    updateStats(data) {
        // Mettre à jour les compteurs
        Object.keys(data).forEach(key => {
            const element = document.getElementById(`stat-${key}`);
            if (element) {
                const currentValue = parseInt(element.textContent);
                const newValue = data[key];
                
                // Animer le changement
                this.animateNumber(element, currentValue, newValue);
            }
        });
    }

    animateNumber(element, start, end) {
        const duration = 500;
        const startTime = performance.now();

        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            const current = Math.floor(start + (end - start) * progress);
            element.textContent = current;

            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };

        requestAnimationFrame(animate);
    }

    initCharts() {
        // Graphique des livraisons
        const ctx = document.getElementById('deliveries-chart');
        if (ctx) {
            this.charts.deliveries = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: this.getTimeLabels(),
                    datasets: [{
                        label: 'Livraisons',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
    }

    updateCharts(data) {
        // Mettre à jour les graphiques avec les nouvelles données
        if (this.charts.deliveries && data.deliveries_timeline) {
            this.charts.deliveries.data.datasets[0].data = data.deliveries_timeline;
            this.charts.deliveries.update();
        }
    }

    getTimeLabels() {
        const labels = [];
        for (let i = 23; i >= 0; i--) {
            const time = new Date();
            time.setHours(time.getHours() - i);
            labels.push(time.getHours() + 'h');
        }
        return labels;
    }

    startAutoRefresh() {
        // Rafraîchir les stats toutes les 30 secondes
        setInterval(() => {
            this.ws.send({ type: 'refresh_stats' });
        }, 30000);
    }
}

// Notifications temps réel
class NotificationManager {
    constructor() {
        this.ws = null;
        this.permission = null;
    }

    async init() {
        // Demander la permission pour les notifications
        await this.requestPermission();
        
        // Connecter WebSocket
        this.connectWebSocket();
    }

    async requestPermission() {
        if ('Notification' in window) {
            this.permission = await Notification.requestPermission();
        }
    }

    connectWebSocket() {
        this.ws = new TransportWebSocket('notifications');

        this.ws.onNewNotification = (notification) => {
            this.showNotification(notification);
            this.updateNotificationBadge();
        };

        this.ws.connect();
    }

    showNotification(data) {
        // Notification navigateur
        if (this.permission === 'granted') {
            new Notification(data.titre, {
                body: data.message,
                icon: '/static/images/logo.png',
                tag: data.id,
                requireInteraction: data.priorite === 'HAUTE'
            });
        }

        // Notification dans l'interface
        this.addToNotificationList(data);
    }

    addToNotificationList(notification) {
        const container = document.getElementById('notifications-list');
        if (!container) return;

        const item = document.createElement('div');
        item.className = `notification-item priority-${notification.priorite.toLowerCase()}`;
        item.innerHTML = `
            <div class="notification-header">
                <strong>${notification.titre}</strong>
                <span class="notification-time">${this.formatTime(notification.date)}</span>
            </div>
            <div class="notification-body">${notification.message}</div>
            <button class="btn-mark-read" data-id="${notification.id}">Marquer comme lu</button>
        `;

        container.prepend(item);

        // Gérer le clic sur "Marquer comme lu"
        item.querySelector('.btn-mark-read').addEventListener('click', (e) => {
            this.markAsRead(notification.id);
            item.remove();
        });
    }

    markAsRead(notificationId) {
        this.ws.send({
            action: 'mark_read',
            notification_id: notificationId
        });
    }

    markAllAsRead() {
        this.ws.send({
            action: 'mark_all_read'
        });
        
        document.getElementById('notifications-list').innerHTML = '';
        this.updateNotificationBadge();
    }

    updateNotificationBadge() {
        const badge = document.getElementById('notification-badge');
        if (badge) {
            const count = document.querySelectorAll('.notification-item').length;
            badge.textContent = count > 0 ? count : '';
            badge.style.display = count > 0 ? 'block' : 'none';
        }
    }

    formatTime(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = (now - date) / 1000; // différence en secondes

        if (diff < 60) {
            return 'À l\'instant';
        } else if (diff < 3600) {
            return `Il y a ${Math.floor(diff / 60)} minutes`;
        } else if (diff < 86400) {
            return `Il y a ${Math.floor(diff / 3600)} heures`;
        } else {
            return date.toLocaleDateString();
        }
    }
}

// Géolocalisation du transporteur
class TransporterGeolocation {
    constructor(missionId) {
        this.missionId = missionId;
        this.watchId = null;
        this.ws = null;
        this.lastUpdate = null;
        this.updateInterval = 10000; // 10 secondes
    }

    start() {
        if ('geolocation' in navigator) {
            // Connecter WebSocket
            this.ws = new TransportWebSocket('tracking', { missionId: this.missionId });
            this.ws.connect();

            // Commencer le suivi
            this.watchId = navigator.geolocation.watchPosition(
                (position) => this.handlePosition(position),
                (error) => this.handleError(error),
                {
                    enableHighAccuracy: true,
                    timeout: 5000,
                    maximumAge: 0
                }
            );
        } else {
            alert('La géolocalisation n\'est pas supportée par votre navigateur');
        }
    }

    handlePosition(position) {
        const now = Date.now();
        
        // Limiter la fréquence des mises à jour
        if (this.lastUpdate && (now - this.lastUpdate) < this.updateInterval) {
            return;
        }

        this.lastUpdate = now;

        const data = {
            type: 'position_update',
            lat: position.coords.latitude,
            lon: position.coords.longitude,
            speed: position.coords.speed ? position.coords.speed * 3.6 : null, // m/s to km/h
            heading: position.coords.heading,
            accuracy: position.coords.accuracy,
            timestamp: position.timestamp
        };

        // Envoyer via WebSocket
        this.ws.send(data);

        // Mettre à jour l'interface locale
        this.updateLocalDisplay(data);
    }

    handleError(error) {
        console.error('Erreur géolocalisation:', error);
        
        let message;
        switch(error.code) {
            case error.PERMISSION_DENIED:
                message = "Permission de géolocalisation refusée";
                break;
            case error.POSITION_UNAVAILABLE:
                message = "Position non disponible";
                break;
            case error.TIMEOUT:
                message = "Délai d'attente dépassé";
                break;
            default:
                message = "Erreur inconnue";
        }

        this.showError(message);
    }

    updateLocalDisplay(data) {
        const display = document.getElementById('current-position');
        if (display) {
            display.innerHTML = `
                <div>Latitude: ${data.lat.toFixed(6)}</div>
                <div>Longitude: ${data.lon.toFixed(6)}</div>
                ${data.speed ? `<div>Vitesse: ${data.speed.toFixed(1)} km/h</div>` : ''}
                <div>Précision: ${data.accuracy.toFixed(0)} m</div>
            `;
        }
    }

    showError(message) {
        const errorDiv = document.getElementById('geolocation-error');
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
        }
    }

    stop() {
        if (this.watchId) {
            navigator.geolocation.clearWatch(this.watchId);
        }
        if (this.ws) {
            this.ws.disconnect();
        }
    }
}

// Initialisation globale
document.addEventListener('DOMContentLoaded', function() {
    // Détecter la page actuelle et initialiser les composants appropriés
    
    // Page de suivi de mission
    if (document.getElementById('tracking-map')) {
        const missionId = document.getElementById('tracking-map').dataset.missionId;
        const trackingMap = new LiveTrackingMap('tracking-map', missionId);
        trackingMap.init();
    }

    // Dashboard
    if (document.getElementById('realtime-dashboard')) {
        const dashboard = new RealtimeDashboard();
        dashboard.init();
    }

    // Notifications
    if (document.getElementById('notifications-container')) {
        const notificationManager = new NotificationManager();
        notificationManager.init();
    }

    // Géolocalisation transporteur
    if (document.getElementById('start-tracking')) {
        let geolocation = null;
        
        document.getElementById('start-tracking').addEventListener('click', function() {
            const missionId = this.dataset.missionId;
            geolocation = new TransporterGeolocation(missionId);
            geolocation.start();
            
            this.style.display = 'none';
            document.getElementById('stop-tracking').style.display = 'block';
        });

        document.getElementById('stop-tracking').addEventListener('click', function() {
            if (geolocation) {
                geolocation.stop();
            }
            
            this.style.display = 'none';
            document.getElementById('start-tracking').style.display = 'block';
        });
    }
});

// Export des classes pour utilisation externe
window.TransportWebSocket = TransportWebSocket;
window.LiveTrackingMap = LiveTrackingMap;
window.RealtimeDashboard = RealtimeDashboard;
window.NotificationManager = NotificationManager;
window.TransporterGeolocation = TransporterGeolocation;