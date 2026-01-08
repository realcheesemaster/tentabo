import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import i18n from '@/lib/i18n';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
    this.setState({ error, errorInfo });
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 max-w-2xl mx-auto">
          <h1 className="text-2xl font-bold text-red-600 mb-4">{i18n.t('common:something_went_wrong')}</h1>
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <h2 className="text-lg font-semibold mb-2">{i18n.t('common:error_details')}</h2>
            <pre className="text-sm overflow-auto">
              {this.state.error && this.state.error.toString()}
            </pre>
            {this.state.errorInfo && (
              <>
                <h3 className="text-md font-semibold mt-4 mb-2">{i18n.t('common:component_stack')}</h3>
                <pre className="text-sm overflow-auto">
                  {this.state.errorInfo.componentStack}
                </pre>
              </>
            )}
          </div>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            {i18n.t('common:reload_page')}
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}