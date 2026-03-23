import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

interface Match {
  match_id: string;
  team_a: string;
  team_b: string;
  current_time: number;
  score: string;
  ai_predictions: Array<{
    event_type: string;
    predicted_time: number;
    confidence: number;
  }>;
}

interface LeaderboardEntry {
  user_id: string;
  username: string;
  score: number;
  rank: number;
}

const App: React.FC = () => {
  const [matches, setMatches] = useState<Match[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [username, setUsername] = useState('');
  const [userId, setUserId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchMatches();
    fetchLeaderboard();
    const interval = setInterval(() => {
      fetchMatches();
      fetchLeaderboard();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchMatches = async () => {
    try {
      const response = await axios.get(`${API_URL}/matches/active`);
      setMatches(response.data.matches);
    } catch (error) {
      console.error('Error fetching matches:', error);
    }
  };

  const fetchLeaderboard = async () => {
    try {
      const response = await axios.get(`${API_URL}/leaderboard?limit=10`);
      setLeaderboard(response.data.leaderboard);
    } catch (error) {
      console.error('Error fetching leaderboard:', error);
    }
  };

  const registerUser = async () => {
    if (!username.trim()) {
      setMessage('Please enter a username');
      return;
    }
    
    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/users/register`, {
        username: username.trim(),
        email: `${username.trim().toLowerCase()}@example.com`
      });
      setUserId(response.data.id);
      setMessage(`✅ Welcome ${username}! Your ID: ${response.data.id}`);
    } catch (error) {
      setMessage('❌ Registration failed. Make sure backend is running.');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const makePrediction = async (matchId: string, eventType: string, predictedTime: number, confidence: number) => {
    if (!userId) {
      setMessage('Please register first!');
      return;
    }
    
    setLoading(true);
    try {
      await axios.post(`${API_URL}/predictions`, {
        user_id: userId,
        match_id: matchId,
        event_type: eventType,
        predicted_time: predictedTime,
        confidence
      });
      
      const minutes = Math.floor(predictedTime / 60);
      const seconds = Math.floor(predictedTime % 60);
      setMessage(`✅ Prediction submitted! ${eventType.toUpperCase()} at ${minutes}:${seconds.toString().padStart(2, '0')}`);
    } catch (error) {
      setMessage('❌ Failed to submit prediction');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div style={{ minHeight: '100vh', padding: '20px' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        <h1 style={{ 
          fontSize: '48px', 
          fontWeight: 'bold', 
          textAlign: 'center', 
          color: 'white',
          marginBottom: '30px'
        }}>
          🎯 Event Hunter Game
        </h1>
        
        {/* Message Toast */}
        {message && (
          <div style={{
            backgroundColor: message.includes('✅') ? '#10b981' : '#ef4444',
            color: 'white',
            padding: '12px',
            borderRadius: '8px',
            marginBottom: '20px',
            textAlign: 'center',
            animation: 'fadeIn 0.3s'
          }}>
            {message}
          </div>
        )}
        
        {/* Registration */}
        {!userId ? (
          <div style={{
            backgroundColor: 'rgba(255,255,255,0.1)',
            borderRadius: '12px',
            padding: '24px',
            marginBottom: '30px',
            backdropFilter: 'blur(10px)'
          }}>
            <h2 style={{ fontSize: '24px', fontWeight: 'bold', color: 'white', marginBottom: '16px' }}>
              🎮 Join the Game!
            </h2>
            <div style={{ display: 'flex', gap: '12px' }}>
              <input
                type="text"
                placeholder="Enter your username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                style={{
                  flex: 1,
                  padding: '12px',
                  borderRadius: '8px',
                  border: 'none',
                  fontSize: '16px'
                }}
                onKeyPress={(e) => e.key === 'Enter' && registerUser()}
              />
              <button
                onClick={registerUser}
                disabled={loading}
                style={{
                  backgroundColor: '#10b981',
                  color: 'white',
                  padding: '12px 24px',
                  borderRadius: '8px',
                  border: 'none',
                  fontSize: '16px',
                  fontWeight: 'bold',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  opacity: loading ? 0.6 : 1
                }}
              >
                {loading ? '...' : 'Start Playing!'}
              </button>
            </div>
          </div>
        ) : (
          <div style={{
            backgroundColor: '#10b981',
            borderRadius: '12px',
            padding: '16px',
            marginBottom: '30px',
            textAlign: 'center'
          }}>
            <p style={{ color: 'white', fontSize: '18px', fontWeight: 'bold' }}>
              🎮 Playing as: {username} (ID: {userId})
            </p>
          </div>
        )}
        
        {/* Main Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
          {/* Matches */}
          <div>
            <h2 style={{ fontSize: '28px', fontWeight: 'bold', color: 'white', marginBottom: '16px' }}>
              🔥 Live Matches
            </h2>
            {matches.map((match) => (
              <div key={match.match_id} style={{
                backgroundColor: 'rgba(255,255,255,0.1)',
                borderRadius: '12px',
                padding: '20px',
                marginBottom: '20px',
                backdropFilter: 'blur(10px)'
              }}>
                <h3 style={{ fontSize: '24px', fontWeight: 'bold', color: 'white', marginBottom: '8px' }}>
                  {match.team_a} vs {match.team_b}
                </h3>
                <p style={{ fontSize: '18px', color: '#fbbf24', marginBottom: '8px' }}>
                  Score: {match.score} | Time: {formatTime(match.current_time)}
                </p>
                
                <h4 style={{ fontSize: '18px', fontWeight: 'bold', color: 'white', marginTop: '16px', marginBottom: '12px' }}>
                  🤖 AI Predictions:
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
                  {match.ai_predictions.map((pred, idx) => (
                    <button
                      key={idx}
                      onClick={() => makePrediction(match.match_id, pred.event_type, pred.predicted_time, pred.confidence)}
                      disabled={loading || !userId}
                      style={{
                        backgroundColor: '#3b82f6',
                        color: 'white',
                        padding: '12px',
                        borderRadius: '8px',
                        border: 'none',
                        cursor: (loading || !userId) ? 'not-allowed' : 'pointer',
                        opacity: (loading || !userId) ? 0.6 : 1,
                        transition: 'transform 0.2s'
                      }}
                      onMouseEnter={(e) => {
                        if (!loading && userId) e.currentTarget.style.transform = 'scale(1.05)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'scale(1)';
                      }}
                    >
                      <strong>{pred.event_type.toUpperCase()}</strong>
                      <br />
                      at {formatTime(pred.predicted_time)}
                      <br />
                      <span style={{ fontSize: '12px' }}>Confidence: {pred.confidence}%</span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
          
          {/* Leaderboard */}
          <div>
            <h2 style={{ fontSize: '28px', fontWeight: 'bold', color: 'white', marginBottom: '16px' }}>
              🏆 Leaderboard
            </h2>
            <div style={{
              backgroundColor: 'rgba(255,255,255,0.1)',
              borderRadius: '12px',
              padding: '20px',
              backdropFilter: 'blur(10px)'
            }}>
              {leaderboard.length === 0 ? (
                <p style={{ color: 'white', textAlign: 'center' }}>No players yet. Be the first!</p>
              ) : (
                leaderboard.map((entry) => (
                  <div key={entry.user_id} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '12px 0',
                    borderBottom: '1px solid rgba(255,255,255,0.2)'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span style={{ fontSize: '24px' }}>
                        {entry.rank === 1 ? '🥇' : entry.rank === 2 ? '🥈' : entry.rank === 3 ? '🥉' : `${entry.rank}.`}
                      </span>
                      <span style={{ color: 'white', fontWeight: 'bold' }}>{entry.username}</span>
                    </div>
                    <span style={{ color: '#fbbf24', fontWeight: 'bold', fontSize: '18px' }}>{entry.score} pts</span>
                  </div>
                ))
              )}
            </div>
            
            {userId && (
              <div style={{
                backgroundColor: 'rgba(255,255,255,0.1)',
                borderRadius: '12px',
                padding: '20px',
                marginTop: '20px',
                backdropFilter: 'blur(10px)'
              }}>
                <h3 style={{ fontSize: '20px', fontWeight: 'bold', color: 'white', marginBottom: '12px' }}>
                  📊 Your Stats
                </h3>
                <p style={{ color: 'white' }}>
                  User ID: {userId}<br/>
                  Keep predicting to earn points!
                </p>
              </div>
            )}
          </div>
        </div>
        
        <style>{`
          @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
          }
        `}</style>
      </div>
    </div>
  );
};

export default App;
