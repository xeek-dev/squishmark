(function() {
  var ws = new WebSocket("ws://" + location.host + "/dev/livereload");
  ws.onmessage = function() { location.reload(); };
  ws.onclose = function() {
    setTimeout(function() { location.reload(); }, 2000);
  };
})();
