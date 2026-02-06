import { useState, useEffect } from 'react'
import { AlertTriangle, CheckCircle, RefreshCw, ShieldAlert, Activity, Server, Download, PieChart } from 'lucide-react'
import { PieChart as RePieChart, Pie, Cell, ResponsiveContainer, Tooltip as ReTooltip } from 'recharts'

interface AuditItem {
    Timestamp: string
    Namespace: string
    Type: string
    Name: string
    Issue_Level: string
    Issue_Type: string
    Recommendation: string
    Category: string
}

const CATEGORIES = ['All', 'Stability', 'Security', 'FinOps']
const COLORS = {
    CRITICAL: '#ef4444', // Red 500
    HIGH: '#f97316',     // Orange 500
    WARN: '#eab308',     // Yellow 500
}

function App() {
    const [data, setData] = useState<AuditItem[]>([])
    const [loading, setLoading] = useState(false)
    const [lastRun, setLastRun] = useState<string | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [activeCategory, setActiveCategory] = useState('All')

    const fetchReport = async () => {
        try {
            const res = await fetch('http://localhost:8000/api/report')
            const json = await res.json()
            setData(json.data || [])
        } catch (err) {
            console.error(err)
        }
    }

    const runAudit = async () => {
        setLoading(true)
        setError(null)
        try {
            const res = await fetch('http://localhost:8000/api/audit', { method: 'POST' })
            const json = await res.json()
            if (json.status === 'success') {
                setLastRun(new Date().toLocaleTimeString())
                await fetchReport()
            } else {
                setError(json.message || 'Audit failed')
            }
        } catch (err) {
            setError('Failed to connect to backend')
        } finally {
            setLoading(false)
        }
    }

    const downloadCSV = () => {
        if (data.length === 0) return

        const headers = ['Timestamp', 'Namespace', 'Type', 'Name', 'Category', 'Level', 'Issue', 'Recommendation']
        const rows = data.map(i => [
            i.Timestamp, i.Namespace, i.Type, i.Name, i.Category, i.Issue_Level, i.Issue_Type, i.Recommendation
        ])

        const csvContent = "data:text/csv;charset=utf-8,"
            + [headers.join(','), ...rows.map(e => e.map(s => `"${s}"`).join(','))].join('\n')

        const encodedUri = encodeURI(csvContent)
        const link = document.createElement("a")
        link.setAttribute("href", encodedUri)
        link.setAttribute("download", `k8s_audit_report_${new Date().toISOString()}.csv`)
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
    }

    useEffect(() => {
        fetchReport()
    }, [])

    const stats = {
        total: data.length,
        critical: data.filter(i => i.Issue_Level === 'CRITICAL').length,
        high: data.filter(i => i.Issue_Level === 'HIGH').length,
        warn: data.filter(i => i.Issue_Level === 'WARN').length,
    }

    const chartData = [
        { name: 'Critical', value: stats.critical, color: COLORS.CRITICAL },
        { name: 'High', value: stats.high, color: COLORS.HIGH },
        { name: 'Warning', value: stats.warn, color: COLORS.WARN },
    ].filter(d => d.value > 0)

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-8 text-slate-100 font-sans">
            <div className="max-w-7xl mx-auto space-y-8">

                {/* Header */}
                <div className="flex justify-between items-center glass-panel p-6">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-blue-500/10 rounded-lg border border-blue-500/20">
                            <Activity className="w-8 h-8 text-blue-400" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-cyan-300">
                                K8s Stability Auditor
                            </h1>
                            <p className="text-slate-400 text-sm">Cluster Health & Security Inspector</p>
                        </div>
                    </div>
                    <div className="flex gap-3">
                        <button
                            onClick={downloadCSV}
                            disabled={data.length === 0}
                            className="flex items-center gap-2 px-4 py-3 rounded-lg font-medium border border-slate-600 hover:bg-slate-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <Download className="w-5 h-5" />
                            Export CSV
                        </button>
                        <button
                            onClick={runAudit}
                            disabled={loading}
                            className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all
                            ${loading
                                    ? 'bg-slate-700 cursor-not-allowed opacity-50'
                                    : 'bg-blue-600 hover:bg-blue-500 shadow-lg shadow-blue-500/20 hover:scale-105 active:scale-95'
                                }`}
                        >
                            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
                            {loading ? 'Auditing...' : 'Run Audit'}
                        </button>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Stats Grid */}
                    <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-6">
                        <StatCard label="Total Issues" value={stats.total} icon={<Server className="w-5 h-5" />} color="text-slate-200" bg="bg-slate-700/30" />
                        <StatCard label="Critical" value={stats.critical} icon={<ShieldAlert className="w-5 h-5" />} color="text-red-400" bg="bg-red-500/10" border="border-red-500/20" />
                        <StatCard label="High Risk" value={stats.high} icon={<AlertTriangle className="w-5 h-5" />} color="text-orange-400" bg="bg-orange-500/10" border="border-orange-500/20" />
                        <StatCard label="FinOps Waste" value={data.filter(i => i.Category === 'FinOps').length} icon={<CheckCircle className="w-5 h-5" />} color="text-emerald-400" bg="bg-emerald-500/10" border="border-emerald-500/20" />
                    </div>

                    {/* Chart */}
                    <div className="glass-panel p-6 flex flex-col items-center justify-center min-h-[200px]">
                        <h3 className="text-sm font-medium text-slate-400 mb-4 w-full text-left flex items-center gap-2">
                            <PieChart className="w-4 h-4" /> Issue Severity
                        </h3>
                        {chartData.length > 0 ? (
                            <div className="w-full h-[160px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <RePieChart>
                                        <Pie
                                            data={chartData}
                                            innerRadius={50}
                                            outerRadius={70}
                                            paddingAngle={5}
                                            dataKey="value"
                                        >
                                            {chartData.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={entry.color} stroke="none" />
                                            ))}
                                        </Pie>
                                        <ReTooltip
                                            contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f1f5f9' }}
                                            itemStyle={{ color: '#f1f5f9' }}
                                        />
                                    </RePieChart>
                                </ResponsiveContainer>
                            </div>
                        ) : (
                            <div className="text-slate-600 text-sm">No data to display</div>
                        )}
                    </div>
                </div>

                {/* Filter Tabs */}
                <div className="flex gap-4 border-b border-glassBorder pb-1">
                    {CATEGORIES.map(cat => (
                        <button
                            key={cat}
                            onClick={() => setActiveCategory(cat)}
                            className={`px-4 py-2 text-sm font-medium transition-colors ${activeCategory === cat
                                ? 'text-blue-400 border-b-2 border-blue-400'
                                : 'text-slate-500 hover:text-slate-300'
                                }`}
                        >
                            {cat}
                        </button>
                    ))}
                </div>

                {/* Error Banner */}
                {error && (
                    <div className="p-4 bg-red-900/20 border border-red-500/50 rounded-lg text-red-200 flex items-center gap-2">
                        <AlertTriangle className="w-5 h-5" />
                        {error}
                    </div>
                )}

                {/* Results Table */}
                <div className="glass-panel overflow-hidden">
                    <div className="p-6 border-b border-glassBorder flex justify-between items-center">
                        <h2 className="text-lg font-semibold text-slate-200">Audit Results</h2>
                        {lastRun && <span className="text-xs text-slate-500">Last updated: {lastRun}</span>}
                    </div>

                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="bg-slate-900/50 text-slate-400 text-sm uppercase tracking-wider">
                                    <th className="p-4 font-medium">Level</th>
                                    <th className="p-4 font-medium">Category</th>
                                    <th className="p-4 font-medium">Namespace</th>
                                    <th className="p-4 font-medium">Resource</th>
                                    <th className="p-4 font-medium">Issue</th>
                                    <th className="p-4 font-medium">Recommendation</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800 text-sm">
                                {data.filter(i => activeCategory === 'All' || i.Category === activeCategory).length === 0 ? (
                                    <tr>
                                        <td colSpan={6} className="p-8 text-center text-slate-500">
                                            No issues found in this category.
                                        </td>
                                    </tr>
                                ) : (
                                    data
                                        .filter(i => activeCategory === 'All' || i.Category === activeCategory)
                                        .map((item, idx) => (
                                            <tr key={idx} className="hover:bg-slate-800/50 transition-colors">
                                                <td className="p-4">
                                                    <Badge level={item.Issue_Level} />
                                                </td>
                                                <td className="p-4">
                                                    <span className="px-2 py-1 rounded-md text-xs font-bold border border-slate-600/50 bg-slate-800/50 text-slate-300">{item.Category || 'Stability'}</span>
                                                </td>
                                                <td className="p-4 text-slate-300 font-mono">{item.Namespace}</td>
                                                <td className="p-4">
                                                    <div className="flex flex-col">
                                                        <span className="font-medium text-slate-200">{item.Name}</span>
                                                        <span className="text-xs text-slate-500">{item.Type}</span>
                                                    </div>
                                                </td>
                                                <td className="p-4 text-slate-300">{item.Issue_Type}</td>
                                                <td className="p-4 text-slate-400 text-xs max-w-xs">{item.Recommendation}</td>
                                            </tr>
                                        ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    )
}

function StatCard({ label, value, icon, color, bg, border = 'border-transparent' }: any) {
    return (
        <div className={`glass-panel p-5 border ${border} flex items-start justify-between`}>
            <div>
                <p className="text-slate-400 text-sm font-medium mb-1">{label}</p>
                <span className={`text-3xl font-bold ${color}`}>{value}</span>
            </div>
            <div className={`p-2 rounded-lg ${bg} ${color}`}>
                {icon}
            </div>
        </div>
    )
}

function Badge({ level }: { level: string }) {
    const styles: Record<string, string> = {
        CRITICAL: 'bg-red-500/20 text-red-300 border-red-500/30',
        HIGH: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
        WARN: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
    }
    const defaultStyle = 'bg-slate-700/50 text-slate-400 border-slate-600'

    return (
        <span className={`px-2 py-1 rounded-md text-xs font-bold border ${styles[level] || defaultStyle}`}>
            {level}
        </span>
    )
}

export default App
