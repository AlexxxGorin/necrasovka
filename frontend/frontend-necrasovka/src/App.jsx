import { useState, useMemo } from "react";
import YearRangeSlider from "./Slider";


function SnippetToggle({ snippet }) {
  const [expanded, setExpanded] = useState(false);

  const { shortHTML, needsToggle } = useMemo(() => {
    const temp = document.createElement("div");
    temp.innerHTML = snippet;
    const fullText = temp.textContent || temp.innerText || "";

    const maxLength = 300;
    const needsToggle = fullText.length > maxLength;
    const shortText = fullText.slice(0, maxLength) + (needsToggle ? "…" : "");

    // оборачиваем в <div> для рендера HTML
    const shortHTML = needsToggle
      ? `<span>${shortText}</span>`
      : snippet;

    return { shortHTML, needsToggle };
  }, [snippet]);

  return (
    <div className="bg-yellow-50 border rounded p-2">
      <div
        className="whitespace-pre-line text-sm"
        dangerouslySetInnerHTML={{
          __html: expanded ? snippet : shortHTML,
        }}
      />
      {needsToggle && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-blue-600 text-xs mt-1 hover:underline"
        >
          {expanded ? "Скрыть" : "Показать полностью"}
        </button>
      )}
    </div>
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [yearRange, setYearRange] = useState([1500, 2025]);
  const [likes, setLikes] = useState({});
  const [selectedTypes, setSelectedTypes] = useState([]);

  const allTypes = useMemo(() => {
    const s = new Set();
    results.forEach(r => {
      if (r.path_index) s.add(r.path_index);
    });
    return Array.from(s);
  }, [results]);

  const filteredResults = useMemo(() => {
    if (selectedTypes.length === 0) return results;
    return results.filter(r => selectedTypes.includes(r.path_index));
  }, [results, selectedTypes]);

  const sendLike = async (docId, currentQuery) => {
  setLikes((prev) => ({ ...prev, [docId]: true }));
  try {
    await fetch("/like", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ doc_id: docId, query: currentQuery })
    });
    console.log(`👍 Like sent for ${docId}`);
  } catch (err) {
    console.error("Ошибка при отправке лайка:", err);
  }
  };


  const handleSearch = async () => {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams();
    params.set("index", "my-books-index");
    params.set("q", query);
    params.set("start_year", yearRange[0]);
    params.set("end_year", yearRange[1]);

    try {
      const res = await fetch(`/search?${params.toString()}`);
      if (!res.ok) throw new Error("Ошибка загрузки");
      const data = await res.json();
      setResults(data.results || []);
      setTotal(data.total?.value || 0);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };



  return (
  <div className="min-h-screen bg-gray-100 py-10 px-4 sm:px-6 lg:px-8">
    <div className="max-w-4xl mx-auto space-y-6">
      <h1 className="text-3xl font-bold flex items-center gap-2">
        📚 Поиск по Библиотеке
      </h1>

      <div className="flex flex-col sm:flex-row items-center gap-2">
        <input
          className="w-full sm:w-auto flex-grow px-4 py-2 border border-gray-300 rounded shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Например: Маяковский"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
        >
          {loading ? "Поиск..." : "Найти"}
        </button>
      </div>

      <YearRangeSlider
        startYear={yearRange[0]}
        endYear={yearRange[1]}
        onChange={setYearRange}
      />

      {/* --- FILTER UI --- */}
      <div className="flex flex-wrap gap-4 items-center mt-4 mb-2">
        <span className="font-medium">Фильтр по типу:</span>
        {allTypes.map((type) => (
          <label key={type} className="inline-flex items-center space-x-1">
            <input
              type="checkbox"
              value={type}
              checked={selectedTypes.includes(type)}
              onChange={(e) => {
                const t = e.target.value;
                setSelectedTypes(prev =>
                  prev.includes(t)
                    ? prev.filter(x => x !== t)
                    : [...prev, t]
                );
              }}
              className="form-checkbox h-4 w-4"
            />
            <span className="text-sm">{type}</span>
          </label>
        ))}
      </div>

      {error && <p className="text-red-600 text-sm">❌ {error}</p>}
      {total !== null && (
        <p className="text-gray-600 text-sm">🔍 Найдено совпадений: {total}</p>
      )}

      <div className="space-y-4">
        {filteredResults.map((item, index) => (
          <div key={item.id || index} className="bg-white p-4 rounded shadow border">
            <div className="flex flex-wrap gap-2 mb-2 text-sm text-gray-600">
              {item.book_year && (
                <span className="inline-block bg-gray-100 px-2 py-1 rounded">
                  📅 {item.book_year}
                </span>
              )}

              {typeof item.score === "number" && (
                 <span className="inline-block bg-green-100 px-2 py-1 rounded">
                   🔢 {item.score.toFixed(2)}
                 </span>
              )}
                
              {item.lang && (
                <span className="inline-block bg-gray-100 px-2 py-1 rounded">
                  🌍 {item.lang}
                </span>
              )}

              {item.filter_name && (
                <span className="inline-block bg-gray-200 px-2 py-1 rounded font-medium">
                  {item.filter_name}
                </span>
              )}

              {item.matched_by && (
               <span className="inline-block bg-blue-100 px-2 py-1 rounded text-xs uppercase">
                 {item.matched_by === "both"
                   ? "Flat+Nested"
                   : item.matched_by === "nested"
                   ? "Nested"
                   : "Flat"}
               </span>
             )}

              <button
                onClick={() => sendLike(item.id, query)}
                className={`text-sm px-2 py-1 rounded border ${
                  likes[item.id]
                    ? "bg-green-100 border-green-400"
                    : "hover:bg-gray-100"
                }`}
                disabled={likes[item.id]}
              >
                👍 {likes[item.id] ? "Лайкнуто" : "Лайкнуть"}
              </button>
            </div>

            {item.cover_page?.image && (
              <img
                src={item.cover_page.image}
                alt="Обложка"
                className="w-32 h-auto object-cover rounded mb-2 border"
              />
            )}

            <h2 className="text-lg font-semibold mb-1">
              {item.title || "Без названия"}
            </h2>

            {item.description && (
              <p className="text-sm text-gray-700">{item.description}</p>
            )}

            {item.matched_pages?.length > 0 && (
              <div className="mt-4">
                <h3 className="text-sm font-medium mb-1">🔎 Совпадения:</h3>
                <ul className="text-sm space-y-2">
                  {item.matched_pages.map((pg, i) => (
                    <li key={i}>
                      <span className="text-gray-500 text-xs mr-2">
                        Стр. {pg.page || "?"}
                      </span>
                      <SnippetToggle snippet={pg.snippet} />
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  </div>
);
}
