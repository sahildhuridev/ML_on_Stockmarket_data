import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  LabelList,
} from "recharts";

const PEChart = ({ stocks, average }) => {
  const formattedData = stocks.map((stock, index) => ({
    x: index + 1,
    y: stock.pe_ratio,
    ticker: stock.ticker,
  }));

  return (
    <div className="mt-8 bg-white text-gray-900 p-4 rounded shadow">
      <h2 className="text-xl font-bold mb-4">PE Ratio Analysis</h2>

      <ResponsiveContainer width="100%" height={400}>
        <ScatterChart>
          <CartesianGrid />
          <XAxis dataKey="x" tick={false} />
          <YAxis dataKey="y" label={{ value: "PE Ratio", angle: -90, position: "insideLeft" }} />
          <Tooltip />

          <ReferenceLine
            y={average}
            stroke="red"
            strokeDasharray="5 5"
            label="Average PE"
          />

          <Scatter data={formattedData} fill="#3b82f6">
            <LabelList dataKey="ticker" position="bottom" />
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>

      <div className="mt-3 text-sm text-gray-600">
        🔵 Below average = Relatively undervalued | 🔴 Above average = Relatively overvalued
      </div>
    </div>
  );
};

export default PEChart;