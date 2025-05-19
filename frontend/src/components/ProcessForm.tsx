import { useState } from 'react';
import type { FormEvent, ChangeEvent } from 'react';
import { socketService } from '../services/socketService';

interface ProcessFormProps {
  onProcessStart: () => void;
}

const ProcessForm: React.FC<ProcessFormProps> = ({ onProcessStart }) => {
  // Form state
  const [inputMethod, setInputMethod] = useState<'search' | 'urls'>('search');
  const [query, setQuery] = useState('');
  const [urls, setUrls] = useState('');
  const [components, setComponents] = useState({
    extract: true,
    summarize: true,
    write: true
  });
  const [articleType, setArticleType] = useState('detailed');
  const [articleFilename, setArticleFilename] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Handle checkbox changes
  const handleComponentChange = (e: ChangeEvent<HTMLInputElement>) => {
    const { name, checked } = e.target;
    setComponents(prev => ({
      ...prev,
      [name]: checked
    }));
  };

  // Handle form submission
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validate form
    const selectedComponents = Object.entries(components)
      .filter(([, isSelected]) => isSelected)
      .map(([name]) => name);

    if (selectedComponents.length === 0) {
      setError('Please select at least one component to run');
      return;
    }

    // For extraction, validate based on selected input method
    if (components.extract) {
      if (inputMethod === 'search' && !query.trim()) {
        setError('Please enter a search query for web context extraction');
        return;
      }
      if (inputMethod === 'urls' && !urls.trim()) {
        setError('Please enter at least one URL for web context extraction');
        return;
      }
    }

    // Prepare data
    const data = {
      query: query.trim(),
      urls: urls.trim(),
      components: selectedComponents,
      articleType,
      articleFilename: articleFilename.trim()
    };

    // Send request to start process
    setIsSubmitting(true);
    try {
      await socketService.startProcess(data);
      onProcessStart();
    } catch (error) {
      setError(error instanceof Error ? error.message : 'An unknown error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Show/hide article type and filename based on write checkbox
  const showArticleOptions = components.write;

  return (
    <div className="card mb-4">
      <div className="card-header">
        <h2 className="card-title h5 mb-0">Run Process</h2>
      </div>
      <div className="card-body">
        <form onSubmit={handleSubmit}>
          {error && (
            <div className="alert alert-danger" role="alert">
              {error}
            </div>
          )}

          <div className="mb-3">
            <label className="form-label">Input Method</label>
            <div className="d-flex gap-4">
              <div className="form-check">
                <input
                  className="form-check-input"
                  type="radio"
                  id="searchMethod"
                  name="inputMethod"
                  checked={inputMethod === 'search'}
                  onChange={() => setInputMethod('search')}
                />
                <label className="form-check-label" htmlFor="searchMethod">
                  Search Query
                </label>
              </div>
              <div className="form-check">
                <input
                  className="form-check-input"
                  type="radio"
                  id="urlsMethod"
                  name="inputMethod"
                  checked={inputMethod === 'urls'}
                  onChange={() => setInputMethod('urls')}
                />
                <label className="form-check-label" htmlFor="urlsMethod">
                  Source URLs
                </label>
              </div>
            </div>
          </div>

          {inputMethod === 'search' && (
            <div className="mb-3">
              <label htmlFor="query" className="form-label">Search Query</label>
              <input
                type="text"
                className="form-control"
                id="query"
                placeholder="Enter search query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <div className="form-text">Enter a search query to find relevant web content</div>
            </div>
          )}

          {inputMethod === 'urls' && (
            <div className="mb-3">
              <label htmlFor="urls" className="form-label">Source URLs</label>
              <textarea
                className="form-control"
                id="urls"
                rows={3}
                placeholder="Enter URLs (one per line or comma-separated)"
                value={urls}
                onChange={(e) => setUrls(e.target.value)}
              ></textarea>
              <div className="form-text">Enter specific URLs to extract content from</div>
            </div>
          )}

          <div className="mb-3">
            <label className="form-label">Components to Run</label>
            <div className="form-check">
              <input
                className="form-check-input"
                type="checkbox"
                id="extractCheck"
                name="extract"
                checked={components.extract}
                onChange={handleComponentChange}
              />
              <label className="form-check-label" htmlFor="extractCheck">
                Web Context Extraction
              </label>
            </div>
            <div className="form-check">
              <input
                className="form-check-input"
                type="checkbox"
                id="summarizeCheck"
                name="summarize"
                checked={components.summarize}
                onChange={handleComponentChange}
              />
              <label className="form-check-label" htmlFor="summarizeCheck">
                Context Summarization
              </label>
            </div>
            <div className="form-check">
              <input
                className="form-check-input"
                type="checkbox"
                id="writeCheck"
                name="write"
                checked={components.write}
                onChange={handleComponentChange}
              />
              <label className="form-check-label" htmlFor="writeCheck">
                Article Writing
              </label>
            </div>
          </div>

          {showArticleOptions && (
            <>
              <div className="mb-3">
                <label htmlFor="articleType" className="form-label">Article Type</label>
                <select
                  className="form-select"
                  id="articleType"
                  value={articleType}
                  onChange={(e) => setArticleType(e.target.value)}
                >
                  <option value="detailed">Detailed</option>
                  <option value="summarized">Summarized</option>
                  <option value="points">Bullet Points</option>
                </select>
                <div className="form-text">
                  Select the type of article to generate
                </div>
              </div>

              <div className="mb-3">
                <label htmlFor="articleFilename" className="form-label">Article Filename</label>
                <input
                  type="text"
                  className="form-control"
                  id="articleFilename"
                  placeholder="Enter article filename (without extension)"
                  value={articleFilename}
                  onChange={(e) => setArticleFilename(e.target.value)}
                />
              </div>
            </>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                {' '}Starting...
              </>
            ) : (
              'Run Process'
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ProcessForm;
