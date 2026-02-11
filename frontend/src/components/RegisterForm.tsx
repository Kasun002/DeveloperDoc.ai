import { useForm } from 'react-hook-form';
import { register as registerUser, storeTokens } from '../services/authService';

interface RegisterFormProps {
  onSuccess: () => void;
}

interface RegisterFormData {
  email: string;
  password: string;
}

export default function RegisterForm({ onSuccess }: RegisterFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError: setFormError,
  } = useForm<RegisterFormData>({
    mode: 'onSubmit',
  });

  const onSubmit = async (data: RegisterFormData) => {
    try {
      const tokens = await registerUser(data);
      storeTokens(tokens);
      onSuccess();
    } catch (err) {
      setFormError('root', {
        type: 'manual',
        message: err instanceof Error ? err.message : 'Registration failed',
      });
    }
  };

  return (
    <form noValidate onSubmit={handleSubmit(onSubmit)} autoComplete='off' className="space-y-4 w-full">
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
          Email
        </label>
        <input
          id="email"
          type="email"
          {...register('email', {
            required: 'Email is required',
            pattern: {
              value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
              message: 'Please enter a valid email address',
            },
          })}
          className="mt-1 block w-full px-3 py-2 sm:px-4 sm:py-3 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 hover:border-gray-400 disabled:bg-gray-100 disabled:cursor-not-allowed text-base transition-colors"
          disabled={isSubmitting}
        />
        {errors.email && (
          <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
        )}
      </div>

      <div>
        <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
          Password
        </label>
        <input
          id="password"
          type="password"
          {...register('password', {
            required: 'Password is required',
            minLength: {
              value: 6,
              message: 'Password must be at least 6 characters',
            },
          })}
          className="mt-1 block w-full px-3 py-2 sm:px-4 sm:py-3 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 hover:border-gray-400 disabled:bg-gray-100 disabled:cursor-not-allowed text-base transition-colors"
          disabled={isSubmitting}
        />
        {errors.password && (
          <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
        )}
      </div>

      {errors.root && (
        <div className="text-red-600 text-sm p-3 bg-red-50 rounded-md">
          {errors.root.message}
        </div>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        className="text-white bg-brand box-border border border-transparent hover:bg-brand-strong focus:ring-4 focus:ring-brand-medium shadow-xs font-medium leading-5 rounded-base text-sm px-4 py-2.5 focus:outline-none w-full"
      >
        {isSubmitting ? 'Registering...' : 'Register'}
      </button>
    </form>
  );
}
