// static/js/main.js - JavaScript principal pour TransportPro

// Configuration globale
const API_BASE_URL = '/api';
const NOTIFICATION_CHECK_INTERVAL = 60000; // 1 minute
const POSITION_UPDATE_INTERVAL = 10000; // 10 secondes

// Gestionnaire de notifications
class NotificationManager {
    constructor() {
        this.permission = null;
        this.unreadCount = 0;
        this.init();
    }

    async init() {
        // Demander la permission pour les notifications
        if ('Notification' in window && Notification.permission === 'default') {
            this.permission = await Notification.requestPermission();
        }

        // Vérifier les notifications périodiquement
        this.checkNotifications();
        setInterval(() => this.checkNotifications(), NOTIFICATION_CHECK_INTERVAL);
    }

    async checkNotifications() {
        try {
            const response = await fetch(`${API_BASE_URL}/notifications/unread/`);
            const data = await response.json();
            
            this.unreadCount = data.count;
            this.updateBadge(this.unreadCount);
            
            // Afficher les nouvelles notifications
            if (data.new_notifications) {
                data.new_notifications.forEach(notif => {
                    this.showNotification(notif);
                });
            }
        } catch (error) {
            console.error('Erreur lors de la vérification des notifications:', error);
        }
    }

    updateBadge(count) {
        const badge = document.getElementById('notification-badge');
        if (badge) {
            badge.textContent = count > 0 ? count : '';
            badge.style.display = count > 0 ? 'block' : 'none';
        }
    }

    showNotification(data) {
        // Notification navigateur
        if (this.permission === 'granted') {
            const notification = new Notification(data.title, {
                body: data.message,
                icon: '/static/images/logo.png',
                tag: data.id,
                requireInteraction: data.priority === 'HIGH'
            });

            notification.onclick = () => {
                window.focus();
                if (data.url) {
                    window.location.href = data.url;
                }
                notification.close();
            };
        }

        // Notification dans l'interface
        this.showInAppNotification(data);
    }

    showInAppNotification(data) {
        const container = document.getElementById('notification-container') || this.createNotificationContainer();
        
        const notification = document.createElement('div');
        notification.className = `notification-toast alert alert-${data.type || 'info'}`;
        notification.innerHTML = `
            <div class="notification-content">
                <strong>${data.title}</strong>
                <p>${data.message}</p>
            </div>
            <button class="notification-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        container.appendChild(notification);
        
        // Animation d'entrée
        setTimeout(() => notification.classList.add('show'), 10);
        
        // Auto-suppression après 5 secondes
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }

    createNotificationContainer() {
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
        `;
        document.body.appendChild(container);
        return container;
    }
}

// Gestionnaire de cartes
class MapManager {
    constructor(elementId, options = {}) {
        this.elementId = elementId;
        this.map = null;
        this.markers = {};
        this.routes = [];
        this.options = {
            center: { lat: 33.5731, lng: -7.5898 }, // Casablanca
            zoom: 12,
            ...options
        };
    }

    async init() {
        // Attendre que Google Maps soit chargé
        if (!window.google || !window.google.maps) {
            console.warn('Google Maps API non chargée');
            return;
        }

        this.map = new google.maps.Map(document.getElementById(this.elementId), {
            center: this.options.center,
            zoom: this.options.zoom,
            styles: this.getMapStyles(),
            disableDefaultUI: false,
            zoomControl: true,
            mapTypeControl: false,
            scaleControl: true,
            streetViewControl: false,
            rotateControl: false,
            fullscreenControl: true
        });

        this.infoWindow = new google.maps.InfoWindow();
    }

    addMarker(id, position, options = {}) {
        // Supprimer l'ancien marqueur s'il existe
        if (this.markers[id]) {
            this.markers[id].setMap(null);
        }

        const marker = new google.maps.Marker({
            position: position,
            map: this.map,
            title: options.title || '',
            icon: options.icon || this.getDefaultIcon(options.type),
            animation: options.animation || google.maps.Animation.DROP,
            ...options
        });

        // Ajouter une info-bulle
        if (options.info) {
            marker.addListener('click', () => {
                this.infoWindow.setContent(options.info);
                this.infoWindow.open(this.map, marker);
            });
        }

        this.markers[id] = marker;
        return marker;
    }

    updateMarkerPosition(id, newPosition, animate = true) {
        const marker = this.markers[id];
        if (!marker) return;

        if (animate) {
            this.animateMarker(marker, newPosition);
        } else {
            marker.setPosition(newPosition);
        }
    }

    animateMarker(marker, newPosition) {
        const startPosition = marker.getPosition();
        const endPosition = new google.maps.LatLng(newPosition.lat, newPosition.lng);
        
        let progress = 0;
        const animation = setInterval(() => {
            progress += 0.01;
            if (progress > 1) {
                clearInterval(animation);
                return;
            }

            const lat = startPosition.lat() + (endPosition.lat() - startPosition.lat()) * progress;
            const lng = startPosition.lng() + (endPosition.lng() - startPosition.lng()) * progress;
            
            marker.setPosition(new google.maps.LatLng(lat, lng));
        }, 10);
    }

    drawRoute(waypoints, options = {}) {
        const directionsService = new google.maps.DirectionsService();
        const directionsRenderer = new google.maps.DirectionsRenderer({
            map: this.map,
            suppressMarkers: options.suppressMarkers || false,
            polylineOptions: {
                strokeColor: options.color || '#2563eb',
                strokeOpacity: options.opacity || 0.8,
                strokeWeight: options.weight || 5
            }
        });

        const request = {
            origin: waypoints[0],
            destination: waypoints[waypoints.length - 1],
            waypoints: waypoints.slice(1, -1).map(point => ({ location: point, stopover: true })),
            travelMode: google.maps.TravelMode.DRIVING,
            optimizeWaypoints: options.optimize || true
        };

        directionsService.route(request, (result, status) => {
            if (status === 'OK') {
                directionsRenderer.setDirections(result);
                this.routes.push(directionsRenderer);
                
                if (options.callback) {
                    options.callback(result);
                }
            } else {
                console.error('Erreur lors du calcul de l\'itinéraire:', status);
            }
        });
    }

    clearRoutes() {
        this.routes.forEach(route => route.setMap(null));
        this.routes = [];
    }

    fitBounds(padding = 50) {
        const bounds = new google.maps.LatLngBounds();
        
        Object.values(this.markers).forEach(marker => {
            bounds.extend(marker.getPosition());
        });

        if (!bounds.isEmpty()) {
            this.map.fitBounds(bounds, padding);
        }
    }

    getDefaultIcon(type) {
        const icons = {
            pickup: {
                path: google.maps.SymbolPath.CIRCLE,
                fillColor: '#10b981',
                fillOpacity: 0.8,
                strokeColor: 'white',
                strokeWeight: 2,
                scale: 10
            },
            delivery: {
                path: google.maps.SymbolPath.CIRCLE,
                fillColor: '#ef4444',
                fillOpacity: 0.8,
                strokeColor: 'white',
                strokeWeight: 2,
                scale: 10
            },
            truck: {
                url: '/static/images/truck-icon.png',
                scaledSize: new google.maps.Size(40, 40),
                origin: new google.maps.Point(0, 0),
                anchor: new google.maps.Point(20, 20)
            }
        };

        return icons[type] || icons.pickup;
    }

    getMapStyles() {
        return [
            {
                featureType: 'all',
                elementType: 'geometry',
                stylers: [{ color: '#f5f5f5' }]
            },
            {
                featureType: 'water',
                elementType: 'geometry',
                stylers: [{ color: '#e9e9e9' }]
            },
            {
                featureType: 'water',
                elementType: 'labels.text.fill',
                stylers: [{ color: '#9e9e9e' }]
            }
        ];
    }
}

// Gestionnaire de formulaires
class FormHandler {
    constructor(formId) {
        this.form = document.getElementById(formId);
        if (this.form) {
            this.init();
        }
    }

    init() {
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Validation en temps réel
        const inputs = this.form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', () => this.validateField(input));
            input.addEventListener('input', () => this.clearError(input));
        });
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        if (!this.validateForm()) {
            return;
        }

        const submitButton = this.form.querySelector('button[type="submit"]');
        const originalText = submitButton.innerHTML;
        submitButton.innerHTML = '<span class="loading"></span> Envoi en cours...';
        submitButton.disabled = true;

        try {
            const formData = new FormData(this.form);
            const response = await fetch(this.form.action, {
                method: this.form.method,
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCookie('csrftoken')
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.handleSuccess(data);
            } else {
                const error = await response.json();
                this.handleError(error);
            }
        } catch (error) {
            this.handleError({ message: 'Erreur de connexion' });
        } finally {
            submitButton.innerHTML = originalText;
            submitButton.disabled = false;
        }
    }

    validateForm() {
        const inputs = this.form.querySelectorAll('[required]');
        let isValid = true;

        inputs.forEach(input => {
            if (!this.validateField(input)) {
                isValid = false;
            }
        });

        return isValid;
    }

    validateField(field) {
        const value = field.value.trim();
        let isValid = true;
        let errorMessage = '';

        // Validation required
        if (field.hasAttribute('required') && !value) {
            errorMessage = 'Ce champ est obligatoire';
            isValid = false;
        }

        // Validation email
        if (field.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                errorMessage = 'Email invalide';
                isValid = false;
            }
        }

        // Validation téléphone
        if (field.type === 'tel' && value) {
            const phoneRegex = /^[\d\s\-\+\(\)]+$/;
            if (!phoneRegex.test(value) || value.length < 10) {
                errorMessage = 'Numéro de téléphone invalide';
                isValid = false;
            }
        }

        // Validation numérique
        if (field.type === 'number' && value) {
            const min = parseFloat(field.min);
            const max = parseFloat(field.max);
            const numValue = parseFloat(value);

            if (isNaN(numValue)) {
                errorMessage = 'Valeur numérique invalide';
                isValid = false;
            } else if (min && numValue < min) {
                errorMessage = `La valeur minimale est ${min}`;
                isValid = false;
            } else if (max && numValue > max) {
                errorMessage = `La valeur maximale est ${max}`;
                isValid = false;
            }
        }

        if (!isValid) {
            this.showError(field, errorMessage);
        } else {
            this.clearError(field);
        }

        return isValid;
    }

    showError(field, message) {
        const formGroup = field.closest('.form-group');
        if (!formGroup) return;

        // Supprimer l'erreur existante
        this.clearError(field);

        // Ajouter la classe d'erreur
        field.classList.add('is-invalid');

        // Créer le message d'erreur
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        formGroup.appendChild(errorDiv);
    }

    clearError(field) {
        const formGroup = field.closest('.form-group');
        if (!formGroup) return;

        field.classList.remove('is-invalid');
        const errorDiv = formGroup.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    handleSuccess(data) {
        if (data.redirect) {
            window.location.href = data.redirect;
        } else {
            this.showAlert('success', data.message || 'Opération réussie');
            if (data.reset) {
                this.form.reset();
            }
        }
    }

    handleError(error) {
        this.showAlert('danger', error.message || 'Une erreur est survenue');
        
        if (error.fields) {
            Object.keys(error.fields).forEach(fieldName => {
                const field = this.form.querySelector(`[name="${fieldName}"]`);
                if (field) {
                    this.showError(field, error.fields[fieldName][0]);
                }
            });
        }
    }

    showAlert(type, message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        this.form.insertBefore(alertDiv, this.form.firstChild);
        
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }

    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}

// Gestionnaire de recherche en temps réel
class SearchHandler {
    constructor(inputId, resultsId, searchUrl) {
        this.input = document.getElementById(inputId);
        this.results = document.getElementById(resultsId);
        this.searchUrl = searchUrl;
        this.debounceTimer = null;
        
        if (this.input) {
            this.init();
        }
    }

    init() {
        this.input.addEventListener('input', (e) => this.handleSearch(e));
        this.input.addEventListener('focus', () => this.showResults());
        
        // Fermer les résultats en cliquant ailleurs
        document.addEventListener('click', (e) => {
            if (!this.input.contains(e.target) && !this.results.contains(e.target)) {
                this.hideResults();
            }
        });
    }

    handleSearch(e) {
        const query = e.target.value.trim();
        
        // Annuler la recherche précédente
        clearTimeout(this.debounceTimer);
        
        if (query.length < 2) {
            this.hideResults();
            return;
        }

        // Debounce de 300ms
        this.debounceTimer = setTimeout(() => {
            this.search(query);
        }, 300);
    }

    async search(query) {
        try {
            const response = await fetch(`${this.searchUrl}?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            this.displayResults(data.results);
        } catch (error) {
            console.error('Erreur de recherche:', error);
        }
    }

    displayResults(results) {
        if (!results || results.length === 0) {
            this.results.innerHTML = '<div class="search-no-results">Aucun résultat trouvé</div>';
            this.showResults();
            return;
        }

        const html = results.map(result => `
            <div class="search-result-item" data-id="${result.id}">
                <div class="search-result-title">${result.title}</div>
                <div class="search-result-subtitle">${result.subtitle || ''}</div>
            </div>
        `).join('');

        this.results.innerHTML = html;
        this.showResults();

        // Ajouter les événements de clic
        this.results.querySelectorAll('.search-result-item').forEach(item => {
            item.addEventListener('click', () => this.selectResult(item));
        });
    }

    selectResult(item) {
        const id = item.dataset.id;
        const title = item.querySelector('.search-result-title').textContent;
        
        this.input.value = title;
        this.input.dataset.selectedId = id;
        this.hideResults();
        
        // Déclencher un événement personnalisé
        this.input.dispatchEvent(new CustomEvent('result-selected', {
            detail: { id, title }
        }));
    }

    showResults() {
        this.results.style.display = 'block';
    }

    hideResults() {
        this.results.style.display = 'none';
    }
}

// Initialisation globale
document.addEventListener('DOMContentLoaded', function() {
    // Initialiser le gestionnaire de notifications
    window.notificationManager = new NotificationManager();
    
    // Initialiser les tooltips
    initTooltips();
    
    // Initialiser les modals
    initModals();
    
    // Smooth scroll
    initSmoothScroll();
    
    // Lazy loading des images
    initLazyLoading();
});

// Fonctions utilitaires
function initTooltips() {
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(e) {
    const text = e.target.dataset.tooltip;
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip-popup';
    tooltip.textContent = text;
    
    document.body.appendChild(tooltip);
    
    const rect = e.target.getBoundingClientRect();
    tooltip.style.top = `${rect.top - tooltip.offsetHeight - 5}px`;
    tooltip.style.left = `${rect.left + (rect.width - tooltip.offsetWidth) / 2}px`;
    
    setTimeout(() => tooltip.classList.add('show'), 10);
}

function hideTooltip() {
    const tooltips = document.querySelectorAll('.tooltip-popup');
    tooltips.forEach(tooltip => {
        tooltip.classList.remove('show');
        setTimeout(() => tooltip.remove(), 300);
    });
}

function initModals() {
    // Gérer l'ouverture des modals
    document.querySelectorAll('[data-modal-target]').forEach(trigger => {
        trigger.addEventListener('click', (e) => {
            e.preventDefault();
            const modalId = trigger.dataset.modalTarget;
            const modal = document.getElementById(modalId);
            if (modal) {
                openModal(modal);
            }
        });
    });

    // Gérer la fermeture des modals
    document.querySelectorAll('[data-modal-close]').forEach(closeBtn => {
        closeBtn.addEventListener('click', () => {
            const modal = closeBtn.closest('.modal');
            if (modal) {
                closeModal(modal);
            }
        });
    });

    // Fermer en cliquant sur l'overlay
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal(modal);
            }
        });
    });
}

function openModal(modal) {
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    setTimeout(() => modal.classList.add('show'), 10);
}

function closeModal(modal) {
    modal.classList.remove('show');
    setTimeout(() => {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }, 300);
}

function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                const offsetTop = target.offsetTop - 80; // Offset pour la navbar
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });
}

function initLazyLoading() {
    const images = document.querySelectorAll('img[data-src]');
    
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
                observer.unobserve(img);
            }
        });
    });

    images.forEach(img => imageObserver.observe(img));
}

// Export des classes pour utilisation externe
window.MapManager = MapManager;
window.FormHandler = FormHandler;
window.SearchHandler = SearchHandler;