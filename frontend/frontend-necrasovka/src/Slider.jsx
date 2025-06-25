import { useState } from "react";
import { Range } from "react-range";

const MIN = 1500;
const MAX = 2025;

export default function YearRangeSlider({ startYear, endYear, onChange }) {
  const [values, setValues] = useState([startYear || MIN, endYear || MAX]);

  const handleChange = (values) => {
    setValues(values);
    onChange(values);
  };

  return (
    <div className="w-full max-w-md mx-auto">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Год издания: {values[0]} – {values[1]}
      </label>
      <Range
        step={1}
        min={MIN}
        max={MAX}
        values={values}
        onChange={handleChange}
        renderTrack={({ props, children }) => (
          <div
            {...props}
            className="h-2 bg-gray-200 rounded"
            style={{ ...props.style }}
          >
            {children}
          </div>
        )}
        renderThumb={({ props }) => (
          <div
            {...props}
            className="h-4 w-4 bg-blue-500 rounded-full shadow"
          />
        )}
      />
    </div>
  );
}
