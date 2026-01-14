/**
 * TransportPro - Professional Transportation Management System
 * Main JavaScript Application
 */

// ============================================================================
// Global Configuration
// ============================================================================
const TransportSystem = {
    apiBaseUrl: '/api/',
    mapConfig: {
        defaultCenter: { lat: 33.5731, lng: -7.5898 }, // Casablanca
        defaultZoom: 11
    },
    refreshInterval: 30000, // 30 seconds
    toastDuration: 5000
};

// ============================================================================
// Utility Functions
// ============================================================================
const Utils = {
    /**
     * Get CSRF Token from cookie or meta tag
     */
    getCsrfToken: function() {
        // Try from input field first
        const tokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (tokenInput) return tokenInput.value;

        // Try from cookie
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') return value;
        }

        // Try from meta tag
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) return metaTag.content;

        return '';
    },

    /**
     * Show toast notification
     */
    showToast: function(message, type = 'info', duration = TransportSystem.toastDuration) {
        const container = document.getElementById('toast-container') || this.createToastContainer();

        const iconMap = {
            success: 'check-circle',
            danger: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };

        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0 show`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body d-flex align-items-center gap-2">
                    <i class="fas fa-${iconMap[type] || 'info-circle'}"></i>
                    <span>${message}</span>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;

        container.appendChild(toast);

        // Initialize Bootstrap toast
        const bsToast = new bootstrap.Toast(toast, {
            autohide: true,
            delay: duration
        });
        bsToast.show();

        // Remove element after hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });

        return toast;
    },

    /**
     * Create toast container if not exists
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
     * Format date to French locale
     */
    formatDate: function(dateString, options = {}) {
        const defaultOptions = {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        const date = new Date(dateString);
        return date.toLocaleDateString('fr-FR', { ...defaultOptions, ...options });
    },

    /**
     * Format number with thousands separator
     */
    formatNumber: function(num) {
        return new Intl.NumberFormat('fr-FR').format(num);
    },

    /**
     * Make AJAX request with proper error handling
     */
    ajax: function(url, options = {}) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            }
        };

        const config = { ...defaultOptions, ...options };

        if (config.headers) {
            config.headers = { ...defaultOptions.headers, ...config.headers };
        }

        if (config.data && config.method !== 'GET') {
            config.body = JSON.stringify(config.data);
            delete config.data;
        }

        return fetch(url, config)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Erreur HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .catch(error => {
                console.error('Erreur AJAX:', error);
                this.showToast(error.message || 'Erreur de communication avec le serveur', 'danger');
                throw error;
            });
    },

    /**
     * Confirmation dialog
     */
    confirm: function(message, onConfirm, onCancel = null) {
        // Use native confirm for now, can be replaced with modal
        if (confirm(message)) {
            if (typeof onConfirm === 'function') {
                onConfirm();
            }
        } else if (typeof onCancel === 'function') {
            onCancel();
        }
    },

    /**
     * Debounce function
     */
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Throttle function
     */
    throttle: function(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    /**
     * Show loading state on button
     */
    setButtonLoading: function(button, loading = true) {
        if (!button) return;

        if (loading) {
            button.disabled = true;
            button.dataset.originalText = button.innerHTML;
            button.innerHTML = '<span class="spinner spinner-sm me-2"></span>Chargement...';
        } else {
            button.disabled = false;
            if (button.dataset.originalText) {
                button.innerHTML = button.dataset.originalText;
                delete button.dataset.originalText;
            }
        }
    },

    /**
     * Show/hide loading overlay
     */
    showLoading: function(containerId, show = true) {
        const container = document.getElementById(containerId);
        if (!container) return;

        let overlay = container.querySelector('.loading-overlay');

        if (show) {
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.className = 'loading-overlay';
                overlay.innerHTML = `
                    <div class="spinner spinner-lg"></div>
                    <p class="text-muted mb-0">Chargement...</p>
                `;
                container.style.position = 'relative';
                container.appendChild(overlay);
            }
            overlay.style.display = 'flex';
        } else if (overlay) {
            overlay.style.display = 'none';
        }
    }
};

// ============================================================================
// Sidebar Manager
// ============================================================================
const SidebarManager = {
    sidebar: null,
    overlay: null,
    toggleBtn: null,

    init: function() {
        this.sidebar = document.getElementById('sidebar');
        this.toggleBtn = document.getElementById('sidebarToggle');

        if (!this.sidebar) return;

        // Create overlay for mobile
        this.createOverlay();

        // Bind toggle button
        if (this.toggleBtn) {
            this.toggleBtn.addEventListener('click', () => this.toggle());
        }

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth < 992) {
                if (!this.sidebar.contains(e.target) &&
                    !this.toggleBtn.contains(e.target) &&
                    this.sidebar.classList.contains('active')) {
                    this.close();
                }
            }
        });

        // Handle window resize
        window.addEventListener('resize', Utils.debounce(() => {
            if (window.innerWidth >= 992) {
                this.sidebar.classList.remove('active');
                this.overlay.classList.remove('active');
            }
        }, 250));
    },

    createOverlay: function() {
        this.overlay = document.createElement('div');
        this.overlay.className = 'sidebar-overlay';
        document.body.appendChild(this.overlay);

        this.overlay.addEventListener('click', () => this.close());
    },

    toggle: function() {
        this.sidebar.classList.toggle('active');
        this.overlay.classList.toggle('active');
    },

    open: function() {
        this.sidebar.classList.add('active');
        this.overlay.classList.add('active');
    },

    close: function() {
        this.sidebar.classList.remove('active');
        this.overlay.classList.remove('active');
    }
};

// ============================================================================
// Order Manager
// ============================================================================
const CommandeManager = {
    /**
     * Update order status
     */
    updateStatus: function(commandeId, newStatus, button = null) {
        if (button) Utils.setButtonLoading(button, true);

        const url = `/api/commandes/${commandeId}/status/`;
        const data = { statut: newStatus };

        return Utils.ajax(url, { method: 'POST', data })
            .then(response => {
                if (response.success) {
                    Utils.showToast('Statut mis à jour avec succès', 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    Utils.showToast(response.message || 'Erreur lors de la mise à jour', 'danger');
                }
                return response;
            })
            .finally(() => {
                if (button) Utils.setButtonLoading(button, false);
            });
    },

    /**
     * Load order details
     */
    loadDetails: function(commandeId, containerId) {
        Utils.showLoading(containerId, true);

        const url = `/client/api/commandes/${commandeId}/`;

        return Utils.ajax(url)
            .then(data => {
                const container = document.getElementById(containerId);
                if (container) {
                    this.renderDetails(data, container);
                }
                return data;
            })
            .finally(() => {
                Utils.showLoading(containerId, false);
            });
    },

    /**
     * Render order details
     */
    renderDetails: function(commande, container) {
        const statusClass = {
            'en_attente': 'secondary',
            'confirmee': 'info',
            'en_cours': 'warning',
            'livree': 'success',
            'annulee': 'danger'
        };

        container.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <p><strong>Numéro:</strong> ${commande.numero || 'N/A'}</p>
                    <p><strong>Statut:</strong>
                        <span class="badge bg-${statusClass[commande.statut] || 'secondary'}">
                            ${commande.statut_display || commande.statut || 'N/A'}
                        </span>
                    </p>
                    <p><strong>Client:</strong> ${commande.client || 'N/A'}</p>
                    <p><strong>Date création:</strong> ${commande.date_creation ? Utils.formatDate(commande.date_creation) : 'N/A'}</p>
                </div>
                <div class="col-md-6">
                    <p><strong>Poids:</strong> ${commande.poids || 0} kg</p>
                    <p><strong>Volume:</strong> ${commande.volume || 0} m³</p>
                    <p><strong>Transporteur:</strong> ${commande.transporteur || 'Non assigné'}</p>
                    <p><strong>Prix estimé:</strong> ${commande.prix ? Utils.formatNumber(commande.prix) + ' DH' : 'N/A'}</p>
                </div>
            </div>
            ${commande.adresse_enlevement ? `
                <hr>
                <div class="row">
                    <div class="col-md-6">
                        <p><strong><i class="fas fa-map-marker-alt text-primary"></i> Enlèvement:</strong></p>
                        <p class="text-muted">${commande.adresse_enlevement}</p>
                    </div>
                    <div class="col-md-6">
                        <p><strong><i class="fas fa-flag-checkered text-success"></i> Livraison:</strong></p>
                        <p class="text-muted">${commande.adresse_livraison || 'N/A'}</p>
                    </div>
                </div>
            ` : ''}
        `;
    },

    /**
     * Delete order
     */
    delete: function(commandeId, button = null) {
        Utils.confirm('Êtes-vous sûr de vouloir supprimer cette commande ?', () => {
            if (button) Utils.setButtonLoading(button, true);

            return Utils.ajax(`/api/commandes/${commandeId}/supprimer/`, { method: 'DELETE' })
                .then(response => {
                    if (response.success) {
                        Utils.showToast('Commande supprimée', 'success');
                        setTimeout(() => location.reload(), 1000);
                    }
                    return response;
                })
                .finally(() => {
                    if (button) Utils.setButtonLoading(button, false);
                });
        });
    }
};

// ============================================================================
// Map Manager (Placeholder for future implementation)
// ============================================================================
const MapManager = {
    map: null,
    markers: [],

    init: function(containerId, options = {}) {
        const config = { ...TransportSystem.mapConfig, ...options };
        const container = document.getElementById(containerId);

        if (!container) return;

        // Placeholder - replace with actual map implementation (Leaflet/Google Maps)
        container.innerHTML = `
            <div class="d-flex flex-column align-items-center justify-content-center h-100 bg-light border rounded">
                <i class="fas fa-map-marked-alt fa-4x text-primary mb-3"></i>
                <p class="text-muted mb-2">Carte interactive</p>
                <small class="text-muted">
                    <i class="fas fa-map-pin"></i>
                    Lat: ${config.defaultCenter.lat.toFixed(4)},
                    Lng: ${config.defaultCenter.lng.toFixed(4)}
                </small>
            </div>
        `;
    },

    addMarker: function(lat, lng, title, icon = 'default') {
        console.log(`Marqueur ajouté: ${title} à [${lat}, ${lng}]`);
        this.markers.push({ lat, lng, title, icon });
    },

    clearMarkers: function() {
        this.markers = [];
    },

    drawRoute: function(points) {
        console.log('Itinéraire tracé:', points);
    }
};

// ============================================================================
// Real-time Tracking Manager
// ============================================================================
const TrackingManager = {
    intervalId: null,
    isTracking: false,
    commandeId: null,

    start: function(commandeId) {
        if (this.isTracking) return;

        this.commandeId = commandeId;
        this.isTracking = true;

        // Initial update
        this.updatePosition();

        // Start interval
        this.intervalId = setInterval(() => {
            this.updatePosition();
        }, TransportSystem.refreshInterval);

        Utils.showToast('Suivi en temps réel activé', 'info');
    },

    stop: function() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
        this.isTracking = false;
        this.commandeId = null;
        Utils.showToast('Suivi en temps réel désactivé', 'info');
    },

    updatePosition: function() {
        if (!this.commandeId) return;

        Utils.ajax(`/client/api/suivi/${this.commandeId}/`)
            .then(data => {
                if (data.position) {
                    MapManager.addMarker(
                        data.position.lat,
                        data.position.lng,
                        'Position actuelle',
                        'vehicle'
                    );

                    // Update UI elements if exist
                    const positionElement = document.getElementById('current-position');
                    if (positionElement) {
                        positionElement.textContent = `${data.position.lat.toFixed(4)}, ${data.position.lng.toFixed(4)}`;
                    }

                    const lastUpdateElement = document.getElementById('last-update');
                    if (lastUpdateElement) {
                        lastUpdateElement.textContent = new Date().toLocaleTimeString('fr-FR');
                    }
                }
            })
            .catch(error => {
                console.error('Erreur de suivi:', error);
            });
    }
};

// ============================================================================
// Notification Manager
// ============================================================================
const NotificationManager = {
    count: 0,
    badge: null,
    bell: null,

    init: function() {
        this.badge = document.getElementById('notificationCount');
        this.bell = document.getElementById('notificationBell');
        
        if (this.badge) {
            this.updateCount();
            setInterval(() => this.updateCount(), 30000);
        }
        
        if (this.bell) {
            this.bell.addEventListener('click', (e) => {
                e.preventDefault();
                this.showNotifications();
            });
        }
    },

    updateCount: function() {
        fetch('/api/notifications/count/', {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log('Notifications count:', data.count);
            this.setCount(data.count || 0);
        })
        .catch(error => console.error('Erreur notifications:', error));
    },

    setCount: function(count) {
        this.count = count;
        if (this.badge) {
            this.badge.textContent = count > 99 ? '99+' : count;
            this.badge.style.display = count > 0 ? 'inline-block' : 'none';
        }
    },
    
    showNotifications: function() {
        fetch('/api/notifications/', {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            this.displayNotificationModal(data.notifications || []);
        });
    },
    
    displayNotificationModal: function(notifications) {
        // Créer ou récupérer la modal
        let modal = document.getElementById('notificationModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'notificationModal';
            modal.className = 'modal fade';
            modal.innerHTML = `
                <div class="modal-dialog modal-dialog-scrollable">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title"><i class="fas fa-bell"></i> Notifications</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body" id="notificationModalBody"></div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        const modalBody = document.getElementById('notificationModalBody');
        let html = '<div class="list-group">';
        
        if (notifications.length === 0) {
            html += '<div class="p-3 text-center text-muted">Aucune notification</div>';
        } else {
            notifications.forEach(notif => {
                const iconMap = {
                    'success': 'check-circle text-success',
                    'warning': 'exclamation-triangle text-warning',
                    'error': 'exclamation-circle text-danger',
                    'info': 'info-circle text-info'
                };
                const icon = iconMap[notif.type_notification] || 'info-circle text-info';
                
                html += `
                    <div class="list-group-item ${notif.lue ? '' : 'bg-light'}">
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1"><i class="fas fa-${icon}"></i> ${notif.titre}</h6>
                            <small class="text-muted">${new Date(notif.date_creation).toLocaleString('fr-FR')}</small>
                        </div>
                        <p class="mb-1">${notif.message}</p>
                    </div>
                `;
            });
        }
        html += '</div>';
        
        modalBody.innerHTML = html;
        
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
};

// ============================================================================
// Form Validation & Handling
// ============================================================================
const FormManager = {
    init: function() {
        // Auto-validate forms
        const forms = document.querySelectorAll('.needs-validation');
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                if (!form.checkValidity()) {
                    e.preventDefault();
                    e.stopPropagation();
                }
                form.classList.add('was-validated');
            });
        });

        // AJAX forms
        const ajaxForms = document.querySelectorAll('.ajax-form');
        ajaxForms.forEach(form => {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.submitAjaxForm(form);
            });
        });
    },

    submitAjaxForm: function(form) {
        const submitBtn = form.querySelector('[type="submit"]');
        if (submitBtn) Utils.setButtonLoading(submitBtn, true);

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        Utils.ajax(form.action || window.location.href, {
            method: form.method || 'POST',
            data: data
        })
        .then(response => {
            if (response.success) {
                Utils.showToast(response.message || 'Opération réussie', 'success');
                if (response.redirect) {
                    setTimeout(() => {
                        window.location.href = response.redirect;
                    }, 1000);
                } else if (response.reload) {
                    setTimeout(() => location.reload(), 1000);
                }
            } else {
                Utils.showToast(response.message || 'Une erreur est survenue', 'danger');
            }
            return response;
        })
        .finally(() => {
            if (submitBtn) Utils.setButtonLoading(submitBtn, false);
        });
    }
};

// ============================================================================
// Admin Utilities
// ============================================================================
const AdminUtils = {
    /**
     * Delete user with confirmation
     */
    deleteUser: function(userId, button = null) {
        Utils.confirm('Êtes-vous sûr de vouloir supprimer cet utilisateur ?', () => {
            if (button) Utils.setButtonLoading(button, true);

            // Correct API endpoint
            return Utils.ajax(`/admin-panel/api/utilisateurs/${userId}/supprimer/`, {
                method: 'DELETE'
            })
            .then(response => {
                if (response.success) {
                    Utils.showToast('Utilisateur supprimé avec succès', 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    Utils.showToast(response.message || 'Erreur lors de la suppression', 'danger');
                }
                return response;
            })
            .catch(error => {
                Utils.showToast('Erreur lors de la suppression', 'danger');
            })
            .finally(() => {
                if (button) Utils.setButtonLoading(button, false);
            });
        });
    },

    /**
     * Toggle user status
     */
    toggleUserStatus: function(userId, isActive) {
        return Utils.ajax(`/admin-panel/api/utilisateurs/${userId}/toggle-status/`, {
            method: 'POST',
            data: { is_active: !isActive }
        })
        .then(response => {
            if (response.success) {
                Utils.showToast('Statut mis à jour', 'success');
                setTimeout(() => location.reload(), 1000);
            }
            return response;
        });
    }
};

// ============================================================================
// Planificateur Utilities
// ============================================================================
const PlanificateurUtils = {
    /**
     * Optimize route for an order
     */
    optimiserItineraire: function(commandeId, button = null) {
        if (button) Utils.setButtonLoading(button, true);

        return Utils.ajax('/planificateur/api/optimiser/', {
            method: 'POST',
            data: { commande_id: commandeId }
        })
        .then(response => {
            if (response.success) {
                Utils.showToast('Itinéraire optimisé avec succès', 'success');
                setTimeout(() => location.reload(), 1500);
            } else {
                Utils.showToast(response.message || 'Erreur lors de l\'optimisation', 'danger');
            }
            return response;
        })
        .finally(() => {
            if (button) Utils.setButtonLoading(button, false);
        });
    },

    /**
     * Assign transporter to order
     */
    affecterTransporteur: function(commandeId, transporteurId, button = null) {
        if (button) Utils.setButtonLoading(button, true);

        return Utils.ajax(`/planificateur/affecter/${commandeId}/`, {
            method: 'POST',
            data: { transporteur_id: transporteurId }
        })
        .then(response => {
            if (response.success) {
                Utils.showToast('Transporteur affecté avec succès', 'success');
                setTimeout(() => location.reload(), 1500);
            } else {
                Utils.showToast(response.message || 'Erreur lors de l\'affectation', 'danger');
            }
            return response;
        })
        .finally(() => {
            if (button) Utils.setButtonLoading(button, false);
        });
    },

    /**
     * Load available transporters
     */
    loadTransporteurs: function(containerId) {
        Utils.showLoading(containerId, true);

        return Utils.ajax('/planificateur/api/transporteurs/')
            .then(data => {
                const container = document.getElementById(containerId);
                if (container && data.transporteurs) {
                    let html = '';
                    data.transporteurs.forEach(t => {
                        html += `
                            <option value="${t.id}">${t.nom} - ${t.vehicule || 'Sans véhicule'}</option>
                        `;
                    });
                    container.innerHTML = html || '<option value="">Aucun transporteur disponible</option>';
                }
                return data;
            })
            .finally(() => {
                Utils.showLoading(containerId, false);
            });
    }
};

// ============================================================================
// Transporteur Utilities
// ============================================================================
const TransporteurUtils = {
    /**
     * Update position via geolocation
     */
    updatePosition: function() {
        if (!navigator.geolocation) {
            Utils.showToast('Géolocalisation non supportée par votre navigateur', 'warning');
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const { latitude, longitude } = position.coords;

                Utils.ajax('/transporteur/api/position/', {
                    method: 'POST',
                    data: { latitude, longitude }
                })
                .then(response => {
                    if (response.success) {
                        Utils.showToast('Position mise à jour', 'success');

                        const lastUpdate = document.getElementById('derniere-maj');
                        if (lastUpdate) {
                            lastUpdate.textContent = new Date().toLocaleString('fr-FR');
                        }
                    }
                });
            },
            (error) => {
                const messages = {
                    1: 'Permission refusée pour la géolocalisation',
                    2: 'Position non disponible',
                    3: 'Délai d\'attente dépassé'
                };
                Utils.showToast(messages[error.code] || 'Erreur de géolocalisation', 'warning');
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 60000
            }
        );
    },

    /**
     * Start a mission
     */
    startMission: function(missionId) {
        Utils.confirm('Démarrer cette mission ?', () => {
            window.location.href = `/transporteur/mission/${missionId}/statut/`;
        });
    },

    /**
     * Report incident
     */
    reportIncident: function(data) {
        return Utils.ajax('/transporteur/api/incident/', {
            method: 'POST',
            data: data
        })
        .then(response => {
            if (response.success) {
                Utils.showToast('Incident signalé avec succès', 'success');
            }
            return response;
        });
    }
};

// ============================================================================
// Initialize Application
// ============================================================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('TransportPro: Application initialisée');
    
    // Initialize sidebar
    SidebarManager.init();

    // Initialize notifications
    NotificationManager.init();
    console.log('NotificationManager initialisé');

    // Initialize forms
    FormManager.init();

    // Initialize Bootstrap components
    initBootstrapComponents();

    // Initialize maps
    initMaps();

    // Initialize tracking if on tracking page
    initTracking();

    // Add fade-in animation to cards
    animateElements();
});

/**
 * Initialize Bootstrap components
 */
function initBootstrapComponents() {
    // Tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggerList.forEach(el => new bootstrap.Tooltip(el));

    // Popovers
    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
    popoverTriggerList.forEach(el => new bootstrap.Popover(el));
}

/**
 * Initialize map containers
 */
function initMaps() {
    const mapContainers = document.querySelectorAll('.map-container');
    mapContainers.forEach(container => {
        if (container.id) {
            MapManager.init(container.id);
        }
    });
}

/**
 * Initialize tracking on tracking pages
 */
function initTracking() {
    if (document.body.classList.contains('tracking-page')) {
        const commandeId = document.body.dataset.commandeId;
        if (commandeId) {
            TrackingManager.start(commandeId);
        }
    }
}

/**
 * Add animations to elements
 */
function animateElements() {
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 50}ms`;
        card.classList.add('fade-in');
    });
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    TrackingManager.stop();
});

// ============================================================================
// Export for global access
// ============================================================================
window.TransportSystem = TransportSystem;
window.Utils = Utils;
window.SidebarManager = SidebarManager;
window.CommandeManager = CommandeManager;
window.MapManager = MapManager;
window.TrackingManager = TrackingManager;
window.NotificationManager = NotificationManager;
window.FormManager = FormManager;
window.AdminUtils = AdminUtils;
window.PlanificateurUtils = PlanificateurUtils;
window.TransporteurUtils = TransporteurUtils;