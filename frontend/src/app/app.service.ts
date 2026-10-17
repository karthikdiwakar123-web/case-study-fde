import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class AppService {
  private apiUrl = 'http://localhost:8000/api'; 

  constructor(private http: HttpClient) {}

  getWelcomeMessage() {
    return this.http.get<{message: string}>(this.apiUrl);
  }
}
