import React from 'react';

const ResultsCard: React.FC = () => {
  return (
    <div className="card mb-4">
      <div className="card-header">
        <h2 className="card-title h5 mb-0">Results</h2>
      </div>
      <div className="card-body">
        <p>
          The process has completed. You can find the generated files in the
          following locations:
        </p>
        <ul>
          <li>Extracted Context: <code>data/context.json</code></li>
          <li>Summarized Context: <code>data/context.txt</code></li>
          <li>Generated Articles: <code>articles/</code> directory</li>
        </ul>
      </div>
    </div>
  );
};

export default ResultsCard;
