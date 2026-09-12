import React, { createContext, useState, useEffect, useContext } from 'react';

export const UserContext = createContext();

export function UserProvider({ children }) {
  const [user, setUser] = useState({
    role: 'executive',
    defaultTopology: 'enterprise_20n',
    defaultEpisodes: 1000,
    preferences: {},
  });

  // Load from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('onyx_user');
    if (saved) {
      try {
        setUser(JSON.parse(saved));
      } catch (e) {
        console.warn('Failed to parse saved user:', e);
      }
    }
  }, []);

  // Save to localStorage when user changes
  useEffect(() => {
    localStorage.setItem('onyx_user', JSON.stringify(user));
  }, [user]);

  const updateUser = (updates) => {
    setUser((prev) => ({ ...prev, ...updates }));
  };

  const setRole = (role) => {
    setUser((prev) => ({ ...prev, role }));
  };

  const setPreferences = (preferences) => {
    setUser((prev) => ({
      ...prev,
      preferences: { ...prev.preferences, ...preferences },
    }));
  };

  return (
    <UserContext.Provider value={{ user, setUser, updateUser, setRole, setPreferences }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within UserProvider');
  }
  return context;
}
