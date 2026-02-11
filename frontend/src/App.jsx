import { AppRouter } from './routes/AppRouter'
import { Toaster } from 'react-hot-toast'

function App() {
  return (
    <>
      <AppRouter />
      <Toaster
        position="top-right"
        reverseOrder={false}
        gutter={8}
        toastOptions={{
          duration: 4000,
          style: {
            fontSize: '14px',
            maxWidth: '500px',
          },
          success: {
            duration: 4000,
          },
          error: {
            duration: 5000,
          },
        }}
      />
    </>
  )
}

export default App
