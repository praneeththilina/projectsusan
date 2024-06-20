// Define the colors for the bar chart
const barChartColor = ['#007bff', '#0056b3'];
// Define the colors for the line chart
const lineChartColor = ['rgba(75, 192, 192, 0.2)', 'rgba(75, 192, 192, 1)', 'rgba(153, 102, 255, 0.2)', 'rgba(153, 102, 255, 1)'];

// Fetch the data from the Flask route
fetch('/data/trades')
    .then(response => response.json())
    .then(data => {
        const trades = data.trades;
        const additionalData = data.additional_data;

        // Process the data to get labels and dataset
        const labels = trades.map(trade => new Date(trade.timestamp).toLocaleDateString());
        const tradeData = trades.map(trade => trade.realized_pnl);

        // Remove duplicates from labels (optional, depending on how your data is structured)
        const uniqueLabels = [...new Set(labels)];

        // Calculate data for the bar chart
        const barChartData = uniqueLabels.map(label => {
            // Find trades for this label
            const tradesForLabel = trades.filter(trade => new Date(trade.timestamp).toLocaleDateString() === label);
            // Sum realized_pnl for this label
            return tradesForLabel.reduce((sum, trade) => sum + trade.realized_pnl, 0);
        });

        // Get the canvas context for the chart
        const ctx = document.getElementById('myBarChart').getContext('2d');

        // Create the bar chart
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: uniqueLabels,
                datasets: [{
                    label: 'Realized PnL',
                    backgroundColor: barChartColor[0],
                    borderColor: barChartColor[0],
                    borderWidth: 1,
                    hoverBackgroundColor: barChartColor[1],
                    hoverBorderColor: barChartColor[1],
                    data: barChartData,
                }]
            },
            options: {
                responsive: true,
                scales: {
                    x: {
                        beginAtZero: true,
                    },
                    y: {
                        beginAtZero: true,
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(tooltipItem) {
                                return `Realized PnL: ${tooltipItem.raw}`;
                            }
                        }
                    }
                }
            }
        });

        // Prepare data for the cumulative PnL line chart
        const cumulativePnlData = {};
        trades.forEach(trade => {
            const date = new Date(trade.timestamp).toLocaleDateString();
            if (!cumulativePnlData[date]) {
                cumulativePnlData[date] = 0;
            }
            cumulativePnlData[date] += trade.realized_pnl;
        });

        // Create an array of dates sorted in ascending order
        const dates = Object.keys(cumulativePnlData).sort((a, b) => new Date(a) - new Date(b));

        // Calculate cumulative PnL
        let cumulativePnL = 0;
        const cumulativePnLArray = dates.map(date => {
            cumulativePnL += cumulativePnlData[date];
            return cumulativePnL;
        });

        // Prepare data for comparison
        const compareData = {}; // Adjust this to fetch and process the second set of data as needed
        const compareDates = []; // Adjust this to fetch and process the dates for comparison

        // Create the line chart
        const ctx2 = document.getElementById('myLineChart').getContext('2d');
        new Chart(ctx2, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [
                    {
                        label: 'Cumulative PnL',
                        fill: true,
                        lineTension: 0.5,
                        backgroundColor: lineChartColor[0],
                        borderColor: lineChartColor[1],
                        borderCapStyle: 'butt',
                        borderDash: [],
                        borderDashOffset: 0,
                        borderJoinStyle: 'miter',
                        pointBorderColor: lineChartColor[1],
                        pointBackgroundColor: '#fff',
                        pointBorderWidth: 1,
                        pointHoverRadius: 5,
                        pointHoverBackgroundColor: lineChartColor[1],
                        pointHoverBorderColor: '#fff',
                        pointHoverBorderWidth: 2,
                        pointRadius: 1,
                        pointHitRadius: 10,
                        data: cumulativePnLArray,
                    },
                    {
                        label: 'Comparison Data', // Adjust this label as needed
                        fill: true,
                        lineTension: 0.5,
                        backgroundColor: lineChartColor[2],
                        borderColor: lineChartColor[3],
                        borderCapStyle: 'butt',
                        borderDash: [],
                        borderDashOffset: 0,
                        borderJoinStyle: 'miter',
                        pointBorderColor: lineChartColor[3],
                        pointBackgroundColor: '#fff',
                        pointBorderWidth: 1,
                        pointHoverRadius: 5,
                        pointHoverBackgroundColor: lineChartColor[3],
                        pointHoverBorderColor: '#eef0f2',
                        pointHoverBorderWidth: 2,
                        pointRadius: 1,
                        pointHitRadius: 10,
                        data: compareData, // Replace with actual comparison data
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            font: {
                                family: 'Poppins'
                            }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            font: {
                                family: 'Poppins'
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        labels: {
                            font: {
                                family: 'Poppins'
                            }
                        }
                    }
                }
            }
        });
    })
    .catch(error => {
        console.error('Error fetching trade data:', error);
    });