function toggleNoteForm() {
    document.getElementById('note-form').classList.toggle('hidden');
}

document.addEventListener('DOMContentLoaded', function () {
    var el = document.getElementById('views-data');
    if (!el) return;

    var viewsData;
    try {
        viewsData = JSON.parse(el.textContent);
    } catch (e) {
        return;
    }

    if (viewsData.length > 0) {
        var ctx = document.getElementById('viewsChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: viewsData.map(function (d) { return d.date; }),
                datasets: [
                    {
                        label: 'Views',
                        data: viewsData.map(function (d) { return d.views; }),
                        borderColor: '#3b82f6',
                        tension: 0.1
                    },
                    {
                        label: 'Unique Visitors',
                        data: viewsData.map(function (d) { return d.unique_visitors; }),
                        borderColor: '#4ade80',
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    }
});
