/* Terminal Theme - Background Effects */
(function() {
    'use strict';

    var container = document.getElementById('bg-canvas-layer');
    if (!container) return;

    var bgType = container.dataset.background;

    if (bgType === 'matrix') initMatrixRain(container);
    else if (bgType === 'noise') initNoise(container);
    else if (bgType === 'hex') initHexWatermark(container);

    function initMatrixRain(container) {
        var canvas = document.createElement('canvas');
        container.appendChild(canvas);
        var ctx = canvas.getContext('2d');

        function resize() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }
        resize();
        window.addEventListener('resize', resize);

        var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@#$%^&*';
        var fontSize = 14;
        var columns = Math.floor(canvas.width / fontSize);
        var drops = Array(columns).fill(1);

        window.addEventListener('resize', function() {
            columns = Math.floor(canvas.width / fontSize);
            drops = Array(columns).fill(1);
        });

        function draw() {
            ctx.fillStyle = 'rgba(13, 17, 23, 0.05)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#4ade80';
            ctx.font = fontSize + 'px "JetBrains Mono", monospace';
            for (var i = 0; i < drops.length; i++) {
                var ch = chars[Math.floor(Math.random() * chars.length)];
                ctx.fillText(ch, i * fontSize, drops[i] * fontSize);
                if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0;
                drops[i]++;
            }
        }
        setInterval(draw, 50);
    }

    function initNoise(container) {
        var canvas = document.createElement('canvas');
        container.appendChild(canvas);
        var ctx = canvas.getContext('2d');

        function resize() {
            canvas.width = Math.floor(window.innerWidth / 2);
            canvas.height = Math.floor(window.innerHeight / 2);
            canvas.style.width = '100%';
            canvas.style.height = '100%';
        }
        resize();
        window.addEventListener('resize', resize);

        function drawNoise() {
            var imageData = ctx.createImageData(canvas.width, canvas.height);
            var data = imageData.data;
            for (var i = 0; i < data.length; i += 4) {
                var v = Math.random() * 255;
                data[i] = v; data[i+1] = v; data[i+2] = v; data[i+3] = 255;
            }
            ctx.putImageData(imageData, 0, 0);
            requestAnimationFrame(drawNoise);
        }
        drawNoise();
    }

    function initHexWatermark(container) {
        var hex = '';
        for (var i = 0; i < 8000; i++) {
            hex += Math.floor(Math.random() * 16).toString(16);
            if (i % 2 === 1) hex += ' ';
            if (i % 64 === 63) hex += '\n';
        }
        container.textContent = hex;
    }
})();
