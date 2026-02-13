import React, { useState } from 'react';

// === Helper Components ===
// (Spinner, SimpleTable, SchemaViewer, QueryResultEntry remain the same)

function Spinner({ size = 'h-5 w-5' }) {
    return (
      <svg className={`animate-spin ${size}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    );
  }

function SimpleTable({ headers, rows }) {
    return (
      <div>
        <div className="w-full overflow-x-auto">
          <div className="align-middle inline-block min-w-full shadow overflow-hidden sm:rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {headers.map((header) => ( <th key={header} scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{header}</th> ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {rows.map((row, rowIndex) => (
                  <tr key={rowIndex}>{row.map((cell, cellIndex) => ( <td key={cellIndex} className="px-4 py-3 whitespace-nowrap text-sm text-gray-800">{cell === null ? 'NULL' : cell}</td> ))}</tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

function SchemaViewer({ dbDetails }) {
    if (!dbDetails) { return ( <div className="flex items-center justify-center my-10"><Spinner /><span className="text-gray-600 ml-2">Loading database...</span></div> ); }
    const tableNames = Object.keys(dbDetails);
    if (tableNames.length === 0) { return <p className="text-gray-500">Database has no tables.</p>; }
    return (
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Database Browser</h3>
        <div className="space-y-8 mb-28">
          {tableNames.map((tableName) => {
            const { content } = dbDetails[tableName];
            return (
              <div key={tableName} className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
                <h4 className="text-lg font-bold text-blue-700 mb-2">{tableName}</h4>
                {content.rows.length > 0 ? ( <SimpleTable headers={content.headers} rows={content.rows} /> ) : ( <p className="text-sm text-gray-500 mt-2">This table is empty.</p> )}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

function QueryResultEntry({ entry }) {
    const { nlQuery, executedSql, result } = entry;

    const renderResult = () => {
      // Case 1: Result is a simple message
      if (typeof result === 'string') {
        const isError = result.toLowerCase().includes('error') || result.toLowerCase().includes('failed');
        const bgColor = isError ? 'bg-red-100 border-red-300' : 'bg-green-100 border-green-300';
        const textColor = isError ? 'text-red-800' : 'text-green-800';
        return ( <div className={`mt-2 p-3 border rounded-lg ${bgColor}`}><p className={`${textColor} font-medium text-sm`}>{result}</p></div> );
      }
      // Case 2: Result is table data
      if (result && Array.isArray(result.headers) && Array.isArray(result.rows)) {
        if (result.rows.length === 0) {
          return ( <div className="mt-2 p-3 bg-gray-100 border border-gray-300 rounded-lg"><p className="text-gray-700 text-sm">Query executed successfully, but returned no rows.</p></div> );
        }
        return <div className="mt-2"><SimpleTable headers={result.headers} rows={result.rows} /></div>;
      }
      // Fallback
      return ( <div className="mt-2 p-3 bg-yellow-100 border border-yellow-300 rounded-lg"><p className="text-yellow-800 font-medium text-sm">Received unexpected result format.</p></div> );
    };

    return (
      <div className="mb-6 p-4 border border-gray-200 rounded-lg bg-white shadow-sm">
        <div className="mb-2 flex gap-2 items-center">
          <span className="text-gray-500 font-semibold text-sm uppercase">You Asked :</span>
          <span className="">{nlQuery}</span>
        </div>
        {executedSql && (
           <div className="my-3 py-2 px-3 bg-gray-100 rounded border flex gap-2 border-gray-300">
             <span className="text-sm font-semibold text-gray-500 uppercase">Executed SQL :</span>
             <pre className="text-sm  mt-1 whitespace-pre-wrap break-words font-mono"><code>{executedSql}</code></pre>
           </div>
        )}
         <div>
           <span className="text-sm font-semibold text-gray-500 uppercase">Result:</span>
           {renderResult()}
         </div>
      </div>
    );
  }

/**
 * === Main Application Component ===
 */
export default function App() {
  const BACKEND_URL = 'http://127.0.0.1:8000';

  const [selectedFile, setSelectedFile] = useState(null);
  const [sessionToken, setSessionToken] = useState(null);
  const [dbDetails, setDbDetails] = useState(null);
  const [naturalQuery, setNaturalQuery] = useState('');
  const [queryHistory, setQueryHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isQueryLoading, setIsQueryLoading] = useState(false);
  const [error, setError] = useState(null);

  const callProcessEndpoint = async (query) => {
    if (!sessionToken) { console.error("No session token"); return; }
    const url = new URL(`${BACKEND_URL}/process`);
    url.searchParams.append('session_token', sessionToken);
    url.searchParams.append('query', query);
    const response = await fetch(url.toString(), { method: 'GET' });
    return await response.json();
  };

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file && file.name.endsWith('.db')) { setSelectedFile(file); setError(null); }
    else { setSelectedFile(null); setError('Please select a valid .db file.'); }
  };

  const handleUpload = async () => {
    if (!selectedFile) { setError('No file selected.'); return; }
    setIsLoading(true); setError(null); setQueryHistory([]);

    const formData = new FormData(); formData.append('file', selectedFile);

    try {
      const response = await fetch(`${BACKEND_URL}/upload_db/`, { method: 'POST', body: formData });
      const data = await response.json();
      if (!response.ok || data.error) { throw new Error(data.error || 'Failed to upload file.'); }
      const token = data.session_token; setSessionToken(token);

      const url = new URL(`${BACKEND_URL}/process`);
      url.searchParams.append('session_token', token);
      url.searchParams.append('query', "__GET_SCHEMA_AND_CONTENT__");
      const schemaResponse = await fetch(url.toString(), { method: 'GET' });
      const schemaData = await schemaResponse.json();
      if (!schemaResponse.ok || schemaData.error || !schemaData.result || schemaData.result.error) { throw new Error(schemaData.error || schemaData.result.error || 'Failed to fetch schema'); }
      setDbDetails(schemaData.result.db_details);
    } catch (err) { console.error('Upload/Schema error:', err); setError(err.message); setSessionToken(null); }
    finally { setIsLoading(false); }
  };

  const handleNlpQuerySubmit = async (event) => {
    event.preventDefault();
    const currentNlQuery = naturalQuery.trim();
    if (!currentNlQuery) { setError('Please enter a query.'); return; }

    setIsQueryLoading(true);
    setError(null);

    try {
      const data = await callProcessEndpoint(currentNlQuery);
      const newHistoryEntry = {
        nlQuery: currentNlQuery,
        executedSql: data.executed_sql || null,
        result: data.result || data.error || "No result received",
      };
      setQueryHistory(prevHistory => [newHistoryEntry, ...prevHistory]);
      setNaturalQuery('');

    } catch (err) {
      console.error('Query submission error:', err);
       const errorEntry = { nlQuery: currentNlQuery, executedSql: null, result: `Network Error: ${err.message}` };
       setQueryHistory(prevHistory => [errorEntry, ...prevHistory]);
    } finally {
      setIsQueryLoading(false);
    }
  };

  const handleStartOver = () => {
    setSessionToken(null); setSelectedFile(null); setNaturalQuery('');
    setQueryHistory([]); setError(null); setDbDetails(null);
  };

  // === RENDER ===
  return (
    // --- UPDATED: Outer container is now flex column taking full screen height ---
    <div className="h-screen bg-white font-sans flex flex-col">
        {/* --- Header (fixed height) --- */}
        <div className="p-2 md:p-4 border-b border-gray-200"> {/* Adjusted padding */}
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900 text-center"> NLP to SQL Converter </h1>
          {!sessionToken && ( <p className="text-gray-600 text-center text-sm md:text-base mt-1"> Upload your SQLite database (.db) file. </p> )}
        </div>

        {/* --- Error Message (appears below header if present) --- */}
        {error && ( <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-3 mx-4 my-2 text-sm" role="alert"> <p className="font-bold">Error</p> <p>{error}</p> </div> )} {/* Adjusted padding/margin/size */}

        {/* --- Main Content Area (grows to fill remaining space) --- */}
        <div className="flex-grow overflow-hidden"> {/* Added overflow-hidden */}
            {!sessionToken ? (
              // === STAGE 1: FILE UPLOAD ===
              <div className="p-4 md:p-10"> {/* Adjusted padding */}
                {/* <h2 className="text-xl font-semibold text-gray-800">Step 1: Upload Database</h2> */}
                <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:space-x-4 space-y-4 sm:space-y-0">
                  <input type="file" accept=".db" onChange={handleFileChange} className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer" />
                  <button onClick={handleUpload} disabled={!selectedFile || isLoading} className="w-full sm:w-auto flex justify-center items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400 disabled:cursor-not-allowed transition-all"> {isLoading ? <Spinner size="h-5 w-5 -ml-1 mr-3" /> : 'Upload'} </button>
                </div>
                {selectedFile && <p className="text-sm text-gray-600 mt-3">Selected file: {selectedFile.name}</p>}
              </div>
            ) : (
              // === STAGE 2: QUERY INTERFACE (Fills parent height) ===
              // --- UPDATED: Added h-full to make it fill the flex-grow parent ---
              <div className="h-full">
                <div className="p-3 md:px-6 flex justify-between items-center border-b border-gray-200"> {/* Adjusted padding */}
                  <p className="text-xs md:text-sm text-green-700 bg-green-50 px-2 py-1 rounded-lg"> <strong>DB:</strong> {selectedFile.name} </p>
                  <button onClick={handleStartOver} className="text-xs md:text-sm text-blue-600 hover:text-blue-800 hover:underline font-medium"> Upload new file </button>
                </div>

                {/* --- UPDATED: Added h-full to make columns fill Stage 2 container --- */}
                <div className="flex flex-col md:flex-row h-full">
                  {/* --- LEFT COLUMN (Scrolls independently) --- */}
                   {/* --- UPDATED: Removed max-h, added h-full --- */}
                  <div className="md:w-[45%] h-full p-4 bg-gray-50 border-r border-gray-200 overflow-y-auto">
                    <SchemaViewer dbDetails={dbDetails} />
                  </div>

                  {/* --- RIGHT COLUMN (Inner part scrolls) --- */}
                   {/* --- UPDATED: Added h-full, overflow-hidden --- */}
                  <div className="md:w-[55%] h-full p-4 flex flex-col overflow-hidden">
                    {/* Query Input Section (Fixed height) */}
                    <div>
                      <form onSubmit={handleNlpQuerySubmit} className="mt-0">
                        {/* <label htmlFor="query" className="block text-sm font-medium text-gray-700"> Enter your question: </label> */}
                        <textarea id="query" rows="2" value={naturalQuery} onChange={(e) => setNaturalQuery(e.target.value)} className="p-3 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-base" placeholder="Enter your query here..."/>
                        <button type="submit" disabled={isQueryLoading} className="mx-auto mt-2 flex justify-center items-center px-4 py-2 border border-transparent text-base font-medium rounded-lg shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400"> {isQueryLoading ? <Spinner size="h-5 w-5 -ml-1 mr-3" /> : 'Run Query'} </button>
                      </form>
                    </div>

                    {/* Executed Queries Log Section (Grows and scrolls) */}
                    {/* --- UPDATED: Added flex-grow --- */}
                    <div className="mt-4 flex-grow overflow-y-auto pr-2 bg-gray-50 p-4 rounded-lg border border-gray-200">
                      {queryHistory.length === 0 ? (
                         <p className="text-gray-500 text-sm">Your query results will appear here.</p>
                      ) : (
                        <div className="space-y-4">
                          {queryHistory.map((entry, index) => (
                            <QueryResultEntry key={index} entry={entry} />
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
        </div>
    </div>
  );
}
