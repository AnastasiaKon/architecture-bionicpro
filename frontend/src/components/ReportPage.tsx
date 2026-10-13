import React, { useMemo, useState } from 'react';
import { useKeycloak } from '@react-keycloak/web';

interface ReportRow {
  report_date: string;
  prosthesis_serial: string;
  model: string;
  events_count: number;
  avg_latency_ms: number;
  max_latency_ms: number;
  slow_responses_count: number;
  avg_signal_quality: number;
  min_battery_level: number;
}

interface Report {
  username: string;
  full_name: string;
  date_from: string;
  date_to: string;
  processed_until: string;
  truncated: boolean;
  generated_at: string;
  rows: ReportRow[];
}

const API_URL = process.env.REACT_APP_API_URL;

const isoDate = (d: Date) => d.toISOString().slice(0, 10);

const ReportPage: React.FC = () => {
  const { keycloak, initialized } = useKeycloak();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<Report | null>(null);

  const today = useMemo(() => new Date(), []);
  const [dateTo, setDateTo] = useState(isoDate(today));
  const [dateFrom, setDateFrom] = useState(
    isoDate(new Date(today.getTime() - 6 * 24 * 3600 * 1000))
  );

  const fetchReport = async (): Promise<Report> => {
    if (!keycloak?.token) {
      throw new Error('Not authenticated');
    }
    await keycloak.updateToken(30);

    const params = new URLSearchParams({ date_from: dateFrom, date_to: dateTo });
    const response = await fetch(`${API_URL}/reports?${params.toString()}`, {
      headers: { Authorization: `Bearer ${keycloak.token}` }
    });

    if (!response.ok) {
      let detail = `${response.status} ${response.statusText}`;
      try {
        const body = await response.json();
        if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
      } catch {}
      throw new Error(detail);
    }
    return (await response.json()) as Report;
  };

  const generateReport = async () => {
    try {
      setLoading(true);
      setError(null);
      setReport(await fetchReport());
    } catch (err) {
      setReport(null);
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const downloadReport = () => {
    if (!report) return;
    const header = [
      'report_date', 'prosthesis_serial', 'model', 'events_count', 'avg_latency_ms',
      'max_latency_ms', 'slow_responses_count', 'avg_signal_quality', 'min_battery_level'
    ];
    const lines = report.rows.map((r) =>
      header.map((h) => String((r as unknown as Record<string, unknown>)[h] ?? '')).join(';')
    );
    const csv = [header.join(';'), ...lines].join('\n');
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `bionicpro-report-${report.username}-${report.date_from}-${report.date_to}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!initialized) {
    return <div>Loading...</div>;
  }

  if (!keycloak.authenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        <button
          onClick={() => keycloak.login()}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Login
        </button>
      </div>
    );
  }

  const username = keycloak.tokenParsed?.preferred_username as string | undefined;

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 py-8">
      <div className="p-8 bg-white rounded-lg shadow-md w-full max-w-4xl">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">Usage Reports</h1>
          <div className="text-sm text-gray-600">
            {username}{' '}
            <button onClick={() => keycloak.logout()} className="ml-2 underline">
              Logout
            </button>
          </div>
        </div>

        <div className="flex flex-wrap gap-4 items-end mb-6">
          <label className="flex flex-col text-sm">
            From
            <input
              type="date"
              value={dateFrom}
              max={dateTo}
              onChange={(e) => setDateFrom(e.target.value)}
              className="border rounded px-2 py-1"
            />
          </label>
          <label className="flex flex-col text-sm">
            To
            <input
              type="date"
              value={dateTo}
              min={dateFrom}
              onChange={(e) => setDateTo(e.target.value)}
              className="border rounded px-2 py-1"
            />
          </label>
          <button
            onClick={generateReport}
            disabled={loading}
            className={`px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 ${
              loading ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            {loading ? 'Generating Report...' : 'Generate Report'}
          </button>
          {report && (
            <button
              onClick={downloadReport}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
            >
              Download CSV
            </button>
          )}
        </div>

        {error && <div className="mb-4 p-4 bg-red-100 text-red-700 rounded">{error}</div>}

        {report && (
          <div>
            <p className="text-sm text-gray-600 mb-2">
              {report.full_name} - {report.date_from} … {report.date_to}. Data processed by
              ETL until {report.processed_until}.
              {report.truncated && (
                <span className="text-orange-600">
                  {' '}
                  Requested period was cut to the processed one.
                </span>
              )}
            </p>
            {report.rows.length === 0 ? (
              <p className="text-gray-500">No data for the selected period.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm border">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-2 py-1 border">Date</th>
                      <th className="px-2 py-1 border">Prosthesis</th>
                      <th className="px-2 py-1 border">Model</th>
                      <th className="px-2 py-1 border">Events</th>
                      <th className="px-2 py-1 border">Avg latency, ms</th>
                      <th className="px-2 py-1 border">Max latency, ms</th>
                      <th className="px-2 py-1 border">Slow (&gt;100 ms)</th>
                      <th className="px-2 py-1 border">Signal quality</th>
                      <th className="px-2 py-1 border">Min battery, %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.rows.map((r) => (
                      <tr key={`${r.report_date}-${r.prosthesis_serial}`}>
                        <td className="px-2 py-1 border">{r.report_date}</td>
                        <td className="px-2 py-1 border">{r.prosthesis_serial}</td>
                        <td className="px-2 py-1 border">{r.model}</td>
                        <td className="px-2 py-1 border text-right">{r.events_count}</td>
                        <td className="px-2 py-1 border text-right">{r.avg_latency_ms.toFixed(1)}</td>
                        <td className="px-2 py-1 border text-right">{r.max_latency_ms}</td>
                        <td className="px-2 py-1 border text-right">{r.slow_responses_count}</td>
                        <td className="px-2 py-1 border text-right">{r.avg_signal_quality.toFixed(2)}</td>
                        <td className="px-2 py-1 border text-right">{r.min_battery_level}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportPage;
