// Copia todos los codigos de respaldo MFA al portapapeles en un click.
// El boton vive en la pagina de generacion (mfa_backup_codes.html); los
// codigos se leen del grid renderizado, que aparece una unica vez.
document.addEventListener('DOMContentLoaded', function () {
    var button = document.getElementById('copy-backup-codes');
    var grid = document.getElementById('backup-codes-grid');
    if (!button || !grid) return;

    function collectCodes() {
        var codes = [];
        grid.querySelectorAll('code').forEach(function (el) {
            var text = el.textContent.trim();
            if (text) codes.push(text);
        });
        return codes.join('\n');
    }

    function copyAll() {
        var text = collectCodes();
        if (!text) return;
        var feedback = function () {
            var original = button.textContent;
            button.textContent = '¡Copiados!';
            button.disabled = true;
            setTimeout(function () {
                button.textContent = original;
                button.disabled = false;
            }, 2500);
        };
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(text).then(feedback).catch(function () {
                fallbackCopy(text, feedback);
            });
        } else {
            fallbackCopy(text, feedback);
        }
    }

    // Fallback para contextos sin Clipboard API (p. ej. HTTP en desarrollo).
    function fallbackCopy(text, onDone) {
        var textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.setAttribute('readonly', '');
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            onDone();
        } catch (err) {
            window.alert('No se pudo copiar automaticamente. Selecciona y copia los codigos manualmente.');
        }
        document.body.removeChild(textarea);
    }

    button.addEventListener('click', copyAll);
});
