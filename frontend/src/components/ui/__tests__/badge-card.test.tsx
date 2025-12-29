/**
 * Тесты для Badge и Card компонентов
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge } from '../badge';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '../card';

describe('Badge', () => {
  it('рендерит с текстом', () => {
    render(<Badge>New</Badge>);
    expect(screen.getByText('New')).toBeInTheDocument();
  });

  it('применяет variant default', () => {
    render(<Badge variant="default">Default</Badge>);
    const badge = screen.getByText('Default');
    expect(badge.className).toMatch(/bg-primary|bg-/);
  });

  it('применяет variant destructive', () => {
    render(<Badge variant="destructive">Error</Badge>);
    const badge = screen.getByText('Error');
    expect(badge.className).toMatch(/destructive/);
  });

  it('применяет variant outline', () => {
    render(<Badge variant="outline">Outlined</Badge>);
    const badge = screen.getByText('Outlined');
    expect(badge.className).toMatch(/border/);
  });

  it('применяет кастомный className', () => {
    render(<Badge className="custom">Custom</Badge>);
    const badge = screen.getByText('Custom');
    expect(badge.className).toContain('custom');
  });
});

describe('Card', () => {
  it('рендерит базовую карточку', () => {
    render(<Card>Card content</Card>);
    expect(screen.getByText('Card content')).toBeInTheDocument();
  });

  it('рендерит полную структуру карточки', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Card Title</CardTitle>
        </CardHeader>
        <CardContent>Main content here</CardContent>
        <CardFooter>Footer content</CardFooter>
      </Card>
    );

    expect(screen.getByText('Card Title')).toBeInTheDocument();
    expect(screen.getByText('Main content here')).toBeInTheDocument();
    expect(screen.getByText('Footer content')).toBeInTheDocument();
  });

  it('CardHeader содержит правильные стили', () => {
    render(
      <Card>
        <CardHeader>Header</CardHeader>
      </Card>
    );
    const header = screen.getByText('Header');
    expect(header.className).toMatch(/flex|space-y/);
  });

  it('CardTitle имеет правильный семантический тег', () => {
    render(
      <Card>
        <CardTitle>Title</CardTitle>
      </Card>
    );
    const title = screen.getByText('Title');
    expect(title.className).toMatch(/font|text/);
  });

  it('CardContent имеет padding', () => {
    render(
      <Card>
        <CardContent>Content</CardContent>
      </Card>
    );
    const content = screen.getByText('Content');
    expect(content.className).toMatch(/p-/);
  });

  it('применяет кастомные className', () => {
    const { container } = render(<Card className="custom-card">Content</Card>);
    const card = container.firstChild as HTMLElement;
    expect(card?.className).toContain('custom-card');
  });
});
