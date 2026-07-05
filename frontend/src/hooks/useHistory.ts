import { useChat } from '../context/ChatContext';

export function useHistory() {
  const { messages, loadingHistory, loadHistory } = useChat();
  return {
    history: messages,
    loading: loadingHistory,
    loadHistory,
  };
}
export default useHistory;
