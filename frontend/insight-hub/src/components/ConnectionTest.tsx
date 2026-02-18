import { useState, useEffect } from 'react';
import { api } from '@/services/api';

export const ConnectionTest = () => {
  const [status, setStatus] = useState<'checking' | 'connected' | 'error'>('checking');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const testConnection = async () => {
      try {
        const health = await api.healthCheck();
        setStatus('connected');
        setMessage(`Connected - ${health.text_vectors} text vectors, ${health.image_vectors} image vectors`);
      } catch (error) {
        setStatus('error');
        setMessage(error instanceof Error ? error.message : 'Failed to connect to backend');
      }
    };

    testConnection();
  }, []);

  return (
    <div className={`p-4 rounded-lg ${
      status === 'connected' ? 'bg-green-100 text-green-800' :
      status === 'error' ? 'bg-red-100 text-red-800' :
      'bg-yellow-100 text-yellow-800'
    }`}>
      <p className="text-sm">
        <strong>Backend Connection:</strong> {status === 'checking' ? 'Checking...' : message}
      </p>
    </div>
  );
};