import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-not-found',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="error-container">
      <div class="error-content">
        <h1 class="error-code">404</h1>
        <h2 class="error-title">Page Not Found</h2>
        <p class="error-message">
          Oops! The page you are looking for doesn't exist, has been removed, or is temporarily unavailable.
        </p>
        <a routerLink="/home" class="home-btn">
          Back to Home
        </a>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      width: 100%;
      min-height: 80vh;
      font-family: system-ui, -apple-system, sans-serif;
    }

    .error-container {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 80vh;
      padding: 20px;
      box-sizing: border-box;
      text-align: center;
      background-color: #f8f9fa;
    }

    .error-content {
      max-width: 500px;
    }

    .error-code {
      font-size: clamp(6rem, 15vw, 10rem);
      font-weight: 900;
      margin: 0;
      line-height: 1;
      background: linear-gradient(135deg, #4f46e5, #06b6d4);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .error-title {
      font-size: 1.75rem;
      color: #1f2937;
      margin-top: 1rem;
      margin-bottom: 0.5rem;
    }

    .error-message {
      color: #4b5563;
      font-size: 1rem;
      line-height: 1.5;
      margin-bottom: 2rem;
    }

    .home-btn {
      display: inline-block;
      background-color: #4f46e5;
      color: #ffffff;
      padding: 0.75rem 1.5rem;
      font-size: 1rem;
      font-weight: 600;
      text-decoration: none;
      border-radius: 0.375rem;
      transition: background-color 0.2s ease, transform 0.1s ease;
      box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2);
    }

    .home-btn:hover {
      background-color: #4338ca;
    }

    .home-btn:active {
      transform: scale(0.98);
    }
  `]
})
export class NotFoundComponent {}
