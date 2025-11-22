import React, { useEffect, useState } from 'react';
import { client } from '../api/client';

interface PlaylistItem {
    id: string;
    url: string;
    title: string;
    position: number;
    created_at: string;
}

interface PlaylistManagerProps {
    token: string;
}

const PlaylistManager: React.FC<PlaylistManagerProps> = ({ token }) => {
    const [items, setItems] = useState<PlaylistItem[]>([]);
    const [newUrl, setNewUrl] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchPlaylist = async () => {
        try {
            const response = await client.get('/api/playlist/');
            setItems(response.data);
        } catch (err) {
            console.error('Failed to fetch playlist', err);
            setError('Failed to load playlist');
        }
    };

    useEffect(() => {
        fetchPlaylist();
    }, [token]);

    const handleAdd = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newUrl) return;

        setLoading(true);
        setError(null);
        try {
            await client.post(
                '/api/playlist/',
                { url: newUrl }
            );
            setNewUrl('');
            fetchPlaylist();
        } catch (err) {
            console.error('Failed to add item', err);
            setError('Failed to add item');
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm('Are you sure you want to delete this item?')) return;

        try {
            await client.delete(`/api/playlist/${id}`);
            fetchPlaylist();
        } catch (err) {
            console.error('Failed to delete item', err);
            setError('Failed to delete item');
        }
    };

    return (
        <div className="bg-white shadow rounded-lg p-6 mt-6">
            <h2 className="text-xl font-bold mb-4">Playlist Management</h2>

            {error && <div className="text-red-500 mb-4">{error}</div>}

            <form onSubmit={handleAdd} className="flex gap-2 mb-6">
                <input
                    type="url"
                    value={newUrl}
                    onChange={(e) => setNewUrl(e.target.value)}
                    placeholder="Enter YouTube URL..."
                    className="flex-1 p-2 border rounded focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    required
                />
                <button
                    type="submit"
                    disabled={loading}
                    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
                >
                    {loading ? 'Adding...' : 'Add Video'}
                </button>
            </form>

            <div className="space-y-2">
                {items.length === 0 ? (
                    <p className="text-gray-500 text-center py-4">Playlist is empty. Add some videos!</p>
                ) : (
                    items.map((item, index) => (
                        <div key={item.id} className="flex items-center justify-between p-3 bg-gray-50 rounded border hover:bg-gray-100 transition">
                            <div className="flex items-center gap-3 overflow-hidden">
                                <span className="text-gray-400 font-mono w-6">{index + 1}.</span>
                                <div className="truncate">
                                    <div className="font-medium truncate">{item.title || item.url}</div>
                                    <div className="text-xs text-gray-500 truncate">{item.url}</div>
                                </div>
                            </div>
                            <button
                                onClick={() => handleDelete(item.id)}
                                className="text-red-500 hover:text-red-700 p-2"
                                title="Delete"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                    <path fillRule="evenodd" d="M9 2a1 1 0 00-.993.883L8 2.999V5H5a1 1 0 00-.993.883L4 5.999V7h12v-1a1 1 0 00-.883-.993L15 5h-3V3a1 1 0 00-.883-.993L11 2H9zM5 8h10a1 1 0 01.993.883L16 9v9a1 1 0 01-.883.993L15 19H5a1 1 0 01-.993-.883L4 18V9a1 1 0 01.883-.993L5 8z" clipRule="evenodd" />
                                </svg>
                            </button>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

export default PlaylistManager;
