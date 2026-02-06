/* Terminal Theme - Pixel Font Renderer */
(function() {
    'use strict';

    const FONT = {
        'A':[[0,1,1,1,0],[1,0,0,0,1],[1,0,0,0,1],[1,1,1,1,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1]],
        'B':[[1,1,1,1,0],[1,0,0,0,1],[1,0,0,0,1],[1,1,1,1,0],[1,0,0,0,1],[1,0,0,0,1],[1,1,1,1,0]],
        'C':[[0,1,1,1,0],[1,0,0,0,1],[1,0,0,0,0],[1,0,0,0,0],[1,0,0,0,0],[1,0,0,0,1],[0,1,1,1,0]],
        'D':[[1,1,1,1,0],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,1,1,1,0]],
        'E':[[1,1,1,1,1],[1,0,0,0,0],[1,0,0,0,0],[1,1,1,1,0],[1,0,0,0,0],[1,0,0,0,0],[1,1,1,1,1]],
        'F':[[1,1,1,1,1],[1,0,0,0,0],[1,0,0,0,0],[1,1,1,1,0],[1,0,0,0,0],[1,0,0,0,0],[1,0,0,0,0]],
        'G':[[0,1,1,1,0],[1,0,0,0,1],[1,0,0,0,0],[1,0,1,1,1],[1,0,0,0,1],[1,0,0,0,1],[0,1,1,1,0]],
        'H':[[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,1,1,1,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1]],
        'I':[[1,1,1],[0,1,0],[0,1,0],[0,1,0],[0,1,0],[0,1,0],[1,1,1]],
        'J':[[0,0,1,1,1],[0,0,0,1,0],[0,0,0,1,0],[0,0,0,1,0],[1,0,0,1,0],[1,0,0,1,0],[0,1,1,0,0]],
        'K':[[1,0,0,0,1],[1,0,0,1,0],[1,0,1,0,0],[1,1,0,0,0],[1,0,1,0,0],[1,0,0,1,0],[1,0,0,0,1]],
        'L':[[1,0,0,0,0],[1,0,0,0,0],[1,0,0,0,0],[1,0,0,0,0],[1,0,0,0,0],[1,0,0,0,0],[1,1,1,1,1]],
        'M':[[1,0,0,0,1],[1,1,0,1,1],[1,0,1,0,1],[1,0,1,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1]],
        'N':[[1,0,0,0,1],[1,1,0,0,1],[1,0,1,0,1],[1,0,1,0,1],[1,0,0,1,1],[1,0,0,0,1],[1,0,0,0,1]],
        'O':[[0,1,1,1,0],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[0,1,1,1,0]],
        'P':[[1,1,1,1,0],[1,0,0,0,1],[1,0,0,0,1],[1,1,1,1,0],[1,0,0,0,0],[1,0,0,0,0],[1,0,0,0,0]],
        'Q':[[0,1,1,1,0],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,1,0,1],[1,0,0,1,0],[0,1,1,0,1]],
        'R':[[1,1,1,1,0],[1,0,0,0,1],[1,0,0,0,1],[1,1,1,1,0],[1,0,1,0,0],[1,0,0,1,0],[1,0,0,0,1]],
        'S':[[0,1,1,1,0],[1,0,0,0,1],[1,0,0,0,0],[0,1,1,1,0],[0,0,0,0,1],[1,0,0,0,1],[0,1,1,1,0]],
        'T':[[1,1,1,1,1],[0,0,1,0,0],[0,0,1,0,0],[0,0,1,0,0],[0,0,1,0,0],[0,0,1,0,0],[0,0,1,0,0]],
        'U':[[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[0,1,1,1,0]],
        'V':[[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[0,1,0,1,0],[0,1,0,1,0],[0,0,1,0,0]],
        'W':[[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,1,0,1],[1,0,1,0,1],[1,1,0,1,1],[1,0,0,0,1]],
        'X':[[1,0,0,0,1],[1,0,0,0,1],[0,1,0,1,0],[0,0,1,0,0],[0,1,0,1,0],[1,0,0,0,1],[1,0,0,0,1]],
        'Y':[[1,0,0,0,1],[1,0,0,0,1],[0,1,0,1,0],[0,0,1,0,0],[0,0,1,0,0],[0,0,1,0,0],[0,0,1,0,0]],
        'Z':[[1,1,1,1,1],[0,0,0,0,1],[0,0,0,1,0],[0,0,1,0,0],[0,1,0,0,0],[1,0,0,0,0],[1,1,1,1,1]],
        'a':[[0,0,0,0,0],[0,0,0,0,0],[0,1,1,1,0],[0,0,0,0,1],[0,1,1,1,1],[1,0,0,0,1],[0,1,1,1,1]],
        'b':[[1,0,0,0,0],[1,0,0,0,0],[1,1,1,1,0],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,1,1,1,0]],
        'c':[[0,0,0,0,0],[0,0,0,0,0],[0,1,1,1,0],[1,0,0,0,0],[1,0,0,0,0],[1,0,0,0,0],[0,1,1,1,0]],
        'd':[[0,0,0,0,1],[0,0,0,0,1],[0,1,1,1,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[0,1,1,1,1]],
        'e':[[0,0,0,0,0],[0,0,0,0,0],[0,1,1,1,0],[1,0,0,0,1],[1,1,1,1,1],[1,0,0,0,0],[0,1,1,1,0]],
        'f':[[0,0,1,1],[0,1,0,0],[1,1,1,0],[0,1,0,0],[0,1,0,0],[0,1,0,0],[0,1,0,0]],
        'g':[[0,0,0,0,0],[0,0,0,0,0],[0,1,1,1,1],[1,0,0,0,1],[0,1,1,1,1],[0,0,0,0,1],[0,1,1,1,0]],
        'h':[[1,0,0,0,0],[1,0,0,0,0],[1,0,1,1,0],[1,1,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1]],
        'i':[[0,0,0],[0,1,0],[0,0,0],[0,1,0],[0,1,0],[0,1,0],[0,1,0]],
        'j':[[0,0,0,0],[0,0,0,1],[0,0,0,0],[0,0,0,1],[0,0,0,1],[1,0,0,1],[0,1,1,0]],
        'k':[[1,0,0,0,0],[1,0,0,0,0],[1,0,0,1,0],[1,0,1,0,0],[1,1,0,0,0],[1,0,1,0,0],[1,0,0,1,0]],
        'l':[[1,1,0],[0,1,0],[0,1,0],[0,1,0],[0,1,0],[0,1,0],[1,1,1]],
        'm':[[0,0,0,0,0],[0,0,0,0,0],[1,1,0,1,0],[1,0,1,0,1],[1,0,1,0,1],[1,0,1,0,1],[1,0,1,0,1]],
        'n':[[0,0,0,0,0],[0,0,0,0,0],[1,0,1,1,0],[1,1,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1]],
        'o':[[0,0,0,0,0],[0,0,0,0,0],[0,1,1,1,0],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[0,1,1,1,0]],
        'p':[[0,0,0,0,0],[0,0,0,0,0],[1,1,1,1,0],[1,0,0,0,1],[1,1,1,1,0],[1,0,0,0,0],[1,0,0,0,0]],
        'q':[[0,0,0,0,0],[0,0,0,0,0],[0,1,1,0,1],[1,0,0,1,1],[0,1,1,0,1],[0,0,0,0,1],[0,0,0,0,1]],
        'r':[[0,0,0,0,0],[0,0,0,0,0],[1,0,1,1,0],[1,1,0,0,1],[1,0,0,0,0],[1,0,0,0,0],[1,0,0,0,0]],
        's':[[0,0,0,0,0],[0,0,0,0,0],[0,1,1,1,0],[1,0,0,0,0],[0,1,1,1,0],[0,0,0,0,1],[1,1,1,1,0]],
        't':[[0,1,0,0],[0,1,0,0],[1,1,1,0],[0,1,0,0],[0,1,0,0],[0,1,0,0],[0,0,1,1]],
        'u':[[0,0,0,0,0],[0,0,0,0,0],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,1,1],[0,1,1,0,1]],
        'v':[[0,0,0,0,0],[0,0,0,0,0],[1,0,0,0,1],[1,0,0,0,1],[0,1,0,1,0],[0,1,0,1,0],[0,0,1,0,0]],
        'w':[[0,0,0,0,0],[0,0,0,0,0],[1,0,0,0,1],[1,0,1,0,1],[1,0,1,0,1],[1,0,1,0,1],[0,1,0,1,0]],
        'x':[[0,0,0,0,0],[0,0,0,0,0],[1,0,0,0,1],[0,1,0,1,0],[0,0,1,0,0],[0,1,0,1,0],[1,0,0,0,1]],
        'y':[[0,0,0,0,0],[0,0,0,0,0],[1,0,0,0,1],[1,0,0,0,1],[0,1,1,1,1],[0,0,0,0,1],[0,1,1,1,0]],
        'z':[[0,0,0,0,0],[0,0,0,0,0],[1,1,1,1,1],[0,0,0,1,0],[0,0,1,0,0],[0,1,0,0,0],[1,1,1,1,1]],
        ' ':[[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]],
        '.':[[0,0],[0,0],[0,0],[0,0],[0,0],[0,0],[1,0]],
        '-':[[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0],[1,1,1,1,1],[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0]],
    };

    function renderPixelText(container, text, pixelSize, gap, opts) {
        opts = opts || {};
        var colorSplit = opts.colorSplit || 0;
        var color1 = opts.color1 || '#3b82f6';
        var color2 = opts.color2 || '#4ade80';
        var addCursor = opts.addCursor || false;
        var cursorStyle = opts.cursorStyle || 'solid';
        var cursorColor = opts.cursorColor || '#4ade80';
        var skewDeg = opts.skewDeg || 0;
        var cursorSkew = opts.cursorSkew || false;

        container.innerHTML = '';
        var outer = document.createElement('div');
        outer.style.display = 'inline-flex';
        outer.style.alignItems = 'start';

        var textWrapper = document.createElement('div');
        textWrapper.style.display = 'inline-flex';
        textWrapper.style.alignItems = 'start';
        textWrapper.style.gap = '0px';
        if (skewDeg !== 0) textWrapper.style.transform = 'skewX(' + skewDeg + 'deg)';

        var charIndex = 0;
        for (var ci = 0; ci < text.length; ci++) {
            var ch = text[ci];
            var grid = FONT[ch];
            if (!grid) { charIndex++; continue; }
            var cols = grid[0].length;
            var rows = grid.length;
            var color = (colorSplit > 0 && charIndex >= colorSplit) ? color2 : color1;

            var letterEl = document.createElement('div');
            letterEl.style.display = 'grid';
            letterEl.style.gridTemplateColumns = 'repeat(' + cols + ', ' + pixelSize + 'px)';
            letterEl.style.gridTemplateRows = 'repeat(' + rows + ', ' + pixelSize + 'px)';
            if (gap > 0) {
                letterEl.style.gap = gap + 'px';
            }
            letterEl.style.marginRight = (pixelSize + gap) + 'px';

            for (var r = 0; r < rows; r++) {
                for (var c = 0; c < cols; c++) {
                    var px = document.createElement('div');
                    if (grid[r][c]) px.style.background = color;
                    letterEl.appendChild(px);
                }
            }
            textWrapper.appendChild(letterEl);
            charIndex++;
        }

        if (addCursor && cursorSkew) {
            textWrapper.appendChild(makeCursor(pixelSize, gap, cursorColor, cursorStyle));
        }
        outer.appendChild(textWrapper);
        if (addCursor && !cursorSkew) {
            outer.appendChild(makeCursor(pixelSize, gap, cursorColor, cursorStyle));
        }
        container.appendChild(outer);
    }

    function makeCursor(pixelSize, gap, color, style) {
        var cursor = document.createElement('div');
        var fullWidth = pixelSize * 5 + gap * 4;
        var w = Math.round(fullWidth * 0.75);
        var h = pixelSize * 7 + gap * 6;
        cursor.style.width = w + 'px';
        cursor.style.height = h + 'px';
        cursor.style.animation = 'blink 1s step-end infinite';
        cursor.style.marginLeft = pixelSize + 'px';
        cursor.style.alignSelf = 'start';
        if (style === 'outline') {
            var borderW = Math.max(1, Math.round(pixelSize * 0.7));
            cursor.style.border = borderW + 'px solid ' + color;
            cursor.style.background = 'transparent';
        } else {
            cursor.style.background = color;
        }
        return cursor;
    }

    /* Auto-initialize on DOMContentLoaded */
    document.addEventListener('DOMContentLoaded', function() {
        var elements = document.querySelectorAll('[data-pixel-text]');
        for (var i = 0; i < elements.length; i++) {
            var el = elements[i];
            var text = el.getAttribute('data-pixel-text');
            var pixelSize = parseInt(el.getAttribute('data-pixel-size'), 10) || 6;
            var gap = parseInt(el.getAttribute('data-pixel-gap'), 10) || 1;
            var cursorAttr = el.getAttribute('data-pixel-cursor');
            var skewDeg = parseFloat(el.getAttribute('data-pixel-skew')) || 0;
            var split = parseInt(el.getAttribute('data-pixel-split'), 10) || 0;
            var color1 = el.getAttribute('data-pixel-color1') || '#3b82f6';
            var color2 = el.getAttribute('data-pixel-color2') || '#4ade80';

            renderPixelText(el, text, pixelSize, gap, {
                colorSplit: split,
                color1: color1,
                color2: color2,
                addCursor: cursorAttr === 'solid' || cursorAttr === 'outline',
                cursorStyle: cursorAttr || 'solid',
                cursorColor: '#4ade80',
                skewDeg: skewDeg,
                cursorSkew: skewDeg !== 0
            });
        }
    });

    /* Export for external use */
    window.renderPixelText = renderPixelText;
    window.makeCursor = makeCursor;
})();
