export const generateId = () =>
  Date.now().toString() +
  Math.random().toString(36).substring(2, 10);
