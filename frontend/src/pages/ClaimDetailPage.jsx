import { useParams } from 'react-router-dom';

export default function ClaimDetailPage() {
  const { id } = useParams();

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          Claim Details: {id}
        </h1>
        <div className="bg-white rounded-lg shadow p-8">
          <p className="text-gray-600 text-center">
            ClaimDetailPage - Coming Soon
          </p>
        </div>
      </div>
    </div>
  );
}
