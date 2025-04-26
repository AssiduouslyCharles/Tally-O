document.addEventListener("DOMContentLoaded", () => {
  const startInput = document.getElementById("insights-start");
  const endInput = document.getElementById("insights-end");
  const refreshBtn = document.getElementById("insights-refresh");
  const ctx = document.getElementById("insights-chart").getContext("2d");
  let chart;

  // initialize inputs to last 30 days
  const today = new Date().toISOString().slice(0, 10);
  endInput.value = today;
  const prior30 = new Date(Date.now() - 1000 * 60 * 60 * 24 * 30)
    .toISOString()
    .slice(0, 10);
  startInput.value = prior30;

  async function loadAndRender() {
    if (chart) {
      chart.destroy();
      chart = null;
    }
    const start = startInput.value;
    const end = endInput.value;
    const res = await fetch(
      `/api/insights-data?start_date=${start}&end_date=${end}`
    );
    const data = await res.json();
    const labels = data.map((d) => d.date);
    const gross = data.map((d) => d.gross);
    const net = data.map((d) => d.net);

    const cfg = {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Gross Sales",
            data: gross,
            fill: false,
            tension: 0.2,
          },
          {
            label: "Net Sales",
            data: net,
            fill: false,
            tension: 0.2,
          },
        ],
      },
      options: {
        scales: {
          x: {
            type: "time",
            time: {
              parser: "YYYY-MM-DD",
              unit: "day",
              displayFormats: { day: "MMM D" },
            },
          },
          y: {
            ticks: { callback: (v) => "$" + v.toFixed(2) },
          },
        },
        plugins: {
          tooltip: {
            callbacks: {
              label: (ctx) =>
                ctx.dataset.label + ": $" + ctx.parsed.y.toFixed(2),
            },
          },
        },
      },
    };

    if (chart) {
      chart.data = cfg.data;
      chart.options = cfg.options;
      chart.update();
    } else {
      chart = new Chart(ctx, cfg);
    }
  }

  refreshBtn.addEventListener("click", loadAndRender);
  loadAndRender();
});
