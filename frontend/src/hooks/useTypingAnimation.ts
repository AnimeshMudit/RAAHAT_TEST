import { useState, useEffect } from 'react';

export function useTypingAnimation(text: string, speed: number = 30, active: boolean = true) {
  const [displayedText, setDisplayedText] = useState('');

  useEffect(() => {
    if (!active) {
      setDisplayedText(text);
      return;
    }

    setDisplayedText('');
    let i = 0;
    const interval = setInterval(() => {
      if (i < text.length) {
        setDisplayedText((prev) => prev + text.charAt(i));
        i++;
      } else {
        clearInterval(interval);
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, speed, active]);

  return displayedText;
}
export default useTypingAnimation;
