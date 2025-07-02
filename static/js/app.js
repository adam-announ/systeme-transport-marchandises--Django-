/**
 * JavaScript principal pour le système de transport
 */

// Configuration globale
const TransportSystem = {
    apiBaseUrl: '/api/',
    mapConfig: {
        defaultCenter: { lat: 33.5731, lng: -7.5898 }, // Casablanca
        defaultZoom: 11
    }
};

// Utilitaires
const Utils = {
    /**
     * Affiche une notification toast
     */
    showToast: function(message, type = 'info') {
        const toastContainer = document.getElementById('toast-container') || this.createToastContainer();
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Supprimer le toast après fermeture
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    },

    /**
     * Crée le conteneur de toasts s'il n'existe pas
     */
    createToastContainer: function() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '1055';
        document.body.appendChild(container);
        return container;
    },

    /**
     * Formate une date
     */
    formatDate: function(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('fr-FR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    /**
     * Effectue une requête AJAX
     */
    ajax: function(url, options = {}) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            }
        };

        const config = { ...defaultOptions, ...options };
        
        if (config.data && config.method !== 'GET') {
            config.body = JSON.stringify(config.data);
        }

        return fetch(url, config)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .catch(error => {
                console.error('Erreur AJAX:', error);
                this.showToast('Erreur de communication avec le serveur', 'danger');
                throw error;
            });
    },

    /**
     * Récupère le token CSRF
     */
    getCsrfToken: function() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    },

    /**
     * Confirme une action
     */
    confirm: function(message, callback) {
        if (confirm(message)) {
            callback();
        }
    }
};

// Gestion des commandes
const CommandeManager = {
    /**
     * Met à jour le statut d'une commande
     */
    updateStatus: function(commandeId, newStatus) {
        const url = `/api/commandes/${commandeId}/status/`;
        const data = { statut: newStatus };

        Utils.ajax(url, { method: 'POST', data })
            .then(response => {
                if (response.success) {
                    Utils.showToast('Statut mis à jour avec succès', 'success');
                    location.reload();
                } else {
                    Utils.showToast('Erreur lors de la mise à jour', 'danger');
                }
            });
    },

    /**
     * Charge les détails d'une commande
     */
    loadDetails: function(commandeId, containerId) {
        const url = `/api/commandes/${commandeId}/`;
        
        Utils.ajax(url)
            .then(data => {
                const container = document.getElementById(containerId);
                if (container) {
                    this.renderCommandeDetails(data, container);
                }
            });
    },

    /**
     * Affiche les détails d'une commande
     */
    renderCommandeDetails: function(commande, container) {
        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h5>Commande ${commande.numero}</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>Statut:</strong> 
                                <span class="badge bg-primary">${commande.statut}</span>
                            </p>
                            <p><strong>Client:</strong> ${commande.client}</p>
                            <p><strong>Date création:</strong> ${Utils.formatDate(commande.date_creation)}</p>
                        </div>
                        <div class="col-md-6">
                            <p><strong>Poids:</strong> ${commande.poids} kg</p>
                            <p><strong>Volume:</strong> ${commande.volume} m³</p>
                            <p><strong>Transporteur:</strong> ${commande.transporteur || 'Non assigné'}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
};

// Gestion des cartes
const MapManager = {
    map: null,
    markers: [],

    /**
     * Initialise une carte
     */
    initMap: function(containerId, options = {}) {
        const config = { ...TransportSystem.mapConfig, ...options };
        
        // Simulation d'une carte (remplacer par Google Maps ou Leaflet)
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `
                <div class="d-flex align-items-center justify-content-center h-100 bg-light border rounded">
                    <div class="text-center">
                        <i class="fas fa-map fa-3x text-muted mb-2"></i>
                        <p class="text-muted">Carte interactive</p>
                        <small class="text-muted">Lat: ${config.defaultCenter.lat}, Lng: ${config.defaultCenter.lng}</small>
                    </div>
                </div>
            `;
        }
    },

    /**
     * Ajoute un marqueur
     */
    addMarker: function(lat, lng, title, icon = 'default') {
        // Simulation d'ajout de marqueur
        console.log(`Marqueur ajouté: ${title} à ${lat}, ${lng}`);
    },

    /**
     * Trace un itinéraire
     */
    drawRoute: function(points) {
        // Simulation de tracé d'itinéraire
        console.log('Itinéraire tracé:', points);
    }
};

// Gestion du suivi en temps réel
const TrackingManager = {
    intervalId: null,
    isTracking: false,

    /**
     * Démarre le suivi
     */
    startTracking: function(commandeId) {
        if (this.isTracking) return;

        this.isTracking = true;
        this.intervalId = setInterval(() => {
            this.updatePosition(commandeId);
        }, 30000); // Mise à jour toutes les 30 secondes

        Utils.showToast('Suivi en temps réel activé', 'info');
    },

    /**
     * Arrête le suivi
     */
    stopTracking: function() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
        this.isTracking = false;
        Utils.showToast('Suivi en temps réel désactivé', 'info');
    },

    /**
     * Met à jour la position
     */
    updatePosition: function(commandeId) {
        const url = `/api/commandes/${commandeId}/position/`;
        
        Utils.ajax(url)
            .then(data => {
                if (data.position) {
                    this.updateMapPosition(data.position);
                }
            })
            .catch(error => {
                console.error('Erreur de suivi:', error);
            });
    },

    /**
     * Met à jour la position sur la carte
     */
    updateMapPosition: function(position) {
        MapManager.addMarker(position.lat, position.lng, 'Position actuelle', 'vehicle');
    }
};

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    // Initialiser les tooltips Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialiser les popovers Bootstrap
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Gestion des formulaires AJAX
    const ajaxForms = document.querySelectorAll('.ajax-form');
    ajaxForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());
            
            Utils.ajax(form.action, {
                method: form.method || 'POST',
                data: data
            })
            .then(response => {
                if (response.success) {
                    Utils.showToast(response.message || 'Opération réussie', 'success');
                    if (response.redirect) {
                        window.location.href = response.redirect;
                    }
                } else {
                    Utils.showToast(response.message || 'Erreur lors de l\'opération', 'danger');
                }
            });
        });
    });

    // Auto-refresh pour les pages de suivi
    if (document.body.classList.contains('tracking-page')) {
        const commandeId = document.body.dataset.commandeId;
        if (commandeId) {
            TrackingManager.startTracking(commandeId);
        }
    }

    // Initialiser les cartes
    const mapContainers = document.querySelectorAll('.map-container');
    mapContainers.forEach(container => {
        MapManager.initMap(container.id);
    });
});

// Nettoyage avant fermeture de la page
window.addEventListener('beforeunload', function() {
    TrackingManager.stopTracking();
});

// Export des modules pour utilisation globale
window.TransportSystem = TransportSystem;
window.Utils = Utils;
window.CommandeManager = CommandeManager;
window.MapManager = MapManager;
window.TrackingManager = TrackingManager;