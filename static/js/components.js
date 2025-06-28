// Composants JavaScript réutilisables pour l'interface

class TransportComponents {
    
    // Composant de notification toast
    static showToast(message, type = 'info', duration = 5000) {
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
        const bsToast = new bootstrap.Toast(toast, { delay: duration });
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }
    
    static createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '1055';
        document.body.appendChild(container);
        return container;
    }
    
    // Composant de modal de confirmation
    static showConfirmModal(title, message, onConfirm, onCancel = null) {
        const modalId = 'confirmModal';
        let modal = document.getElementById(modalId);
        
        if (!modal) {
            modal = document.createElement('div');
            modal.id = modalId;
            modal.className = 'modal fade';
            modal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p>${message}</p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
                            <button type="button" class="btn btn-primary" id="confirmBtn">Confirmer</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        const confirmBtn = modal.querySelector('#confirmBtn');
        const cancelBtn = modal.querySelector('[data-bs-dismiss="modal"]');
        
        confirmBtn.onclick = () => {
            onConfirm();
            bootstrap.Modal.getInstance(modal).hide();
        };
        
        if (onCancel) {
            cancelBtn.onclick = onCancel;
        }
        
        new bootstrap.Modal(modal).show();
    }
    
    // Composant de badge de statut
    static getStatusBadge(status) {
        const statusConfig = {
            'en_attente': { class: 'warning', text: 'En attente' },
            'affectee': { class: 'info', text: 'Affectée' },
            'planifiee': { class: 'primary', text: 'Planifiée' },
            'en_cours': { class: 'success', text: 'En cours' },
            'livree': { class: 'success', text: 'Livrée' },
            'annulee': { class: 'danger', text: 'Annulée' },
            'incident': { class: 'danger', text: 'Incident' }
        };
        
        const config = statusConfig[status] || { class: 'secondary', text: status };
        return `<span class="badge bg-${config.class}">${config.text}</span>`;
    }
}

// Utilitaires
class TransportUtils {
    
    // Formatage des dates
    static formatDate(dateString, format = 'short') {
        const date = new Date(dateString);
        const options = {
            short: { day: '2-digit', month: '2-digit', year: 'numeric' },
            long: { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            }
        };
        
        return date.toLocaleDateString('fr-FR', options[format] || options.short);
    }
    
    // Validation des formulaires
    static validateForm(formId, rules) {
        const form = document.getElementById(formId);
        if (!form) return false;
        
        let isValid = true;
        const errors = {};
        
        Object.keys(rules).forEach(fieldName => {
            const field = form.querySelector(`[name="${fieldName}"]`);
            const rule = rules[fieldName];
            
            if (!field) return;
            
            // Supprimer les anciennes erreurs
            const existingError = field.parentNode.querySelector('.invalid-feedback');
            if (existingError) existingError.remove();
            field.classList.remove('is-invalid');
            
            // Validation
            if (rule.required && !field.value.trim()) {
                errors[fieldName] = rule.messages?.required || 'Ce champ est requis';
                isValid = false;
            } else if (rule.minLength && field.value.length < rule.minLength) {
                errors[fieldName] = rule.messages?.minLength || `Minimum ${rule.minLength} caractères`;
                isValid = false;
            }
            
            // Afficher l'erreur
            if (errors[fieldName]) {
                field.classList.add('is-invalid');
                const errorDiv = document.createElement('div');
                errorDiv.className = 'invalid-feedback';
                errorDiv.textContent = errors[fieldName];
                field.parentNode.appendChild(errorDiv);
            }
        });
        
        return isValid;
    }
    
    // Requêtes API simplifiées
    static async apiRequest(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            credentials: 'same-origin'
        };
        
        const response = await fetch(url, { ...defaultOptions, ...options });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
    
    static getCsrfToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }
}

// Initialisation globale
document.addEventListener('DOMContentLoaded', function() {
    // Initialiser les tooltips Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});