import { Component, inject, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import {AppService} from './app.service';
@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.css'
})

export class App {
  private appService = inject(AppService);
  title='test'
  ngOnInit() {
    this.appService.getWelcomeMessage().subscribe({
         next: (response) =>{this.title = response.message;},
         error: (error) => console.error('Error:', error),
    });    
  }
}
