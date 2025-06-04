import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';
import { Line, Bar, Doughnut } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

const DashboardChart = ({ data, type = 'line', height = 300 }) => {
  const generateMockData = () => {
    // Données d'exemple pour le développement
    const labels = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun'];
    return {
      labels,
      datasets: [
        {
          label: 'Commandes',
          data: [12, 19, 15, 25, 22, 30],
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          tension: 0.4,
        },
        {
          label: 'Livrées',
          data: [10, 16, 13, 22, 20, 28],
          borderColor: 'rgb(34, 197, 94)',
          backgroundColor: 'rgba(34, 197, 94, 0.1)',
          tension: 0.4,
        },
      ],
    };
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: false,
      },
    },
    scales: type !== 'doughnut' ? {
      y: {
        beginAtZero: true,
        grid: {
          color: 'rgba(0, 0, 0, 0.1)',
        },
      },
      x: {
        grid: {
          display: false,
        },
      },
    } : {},
  };

  const chartData = data || generateMockData();

  const renderChart = () => {
    switch (type) {
      case 'bar':
        return <Bar data={chartData} options={options} height={height} />;
      case 'doughnut':
        return <Doughnut data={chartData} options={options} height={height} />;
      default:
        return <Line data={chartData} options={options} height={height} />;
    }
  };

  return (
    <div style={{ height: `${height}px` }}>
      {renderChart()}
    </div>
  );
};

export default DashboardChart;