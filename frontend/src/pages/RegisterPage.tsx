import { useNavigate, Link } from "react-router-dom";
import RegisterForm from "../components/RegisterForm";

const RegisterPage = () => {
  const navigate = useNavigate();

  const handleRegisterSuccess = () => {
    navigate("/chat");
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden">
      <img
        src="/auth_bg.png"
        alt="Background"
        className="absolute inset-0 w-full h-full object-cover opacity-30 pointer-events-none select-none z-0"
      />
      <div className="max-w-md w-full space-y-6 relative z-10">
        <div className="text-center">
          <h2 className="text-3xl font-extrabold text-gray-900">
            Create your account
          </h2>
        </div>

        <div className="bg-white py-8 px-6 shadow-md rounded-lg sm:px-10">
          <RegisterForm onSuccess={handleRegisterSuccess} />
        </div>

        <div className="text-center">
          <p className="text-sm text-gray-600">
            Already have an account?{" "}
            <Link
              to="/login"
              className="font-medium text-blue-600 hover:text-blue-500 hover:underline focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded transition-colors"
            >
              Sign in here
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
